# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Abstract base classes for benchmark runners."""

import abc
import ast
import asyncio
import os
from pathlib import Path
import re
import sys
import tempfile
import textwrap
from typing import Generic
from typing import Optional
from typing import TypeVar

from benchmarks.data_models import ApiUnderstandingBenchmarkCase, MultipleChoiceBenchmarkCase # Moved from within runner properties
from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.data_models import BenchmarkResultType
from benchmarks.data_models import FixErrorBenchmarkCase
from benchmarks.data_models import GeneratedAnswer
import benchmarks.validation_utils as validation_utils

# A TypeVar to create a generic link between a runner and the case it handles.
BenchmarkCaseT = TypeVar("BenchmarkCaseT", bound=BaseBenchmarkCase)


class BenchmarkRunner(abc.ABC, Generic[BenchmarkCaseT]):
  """Abstract base class for benchmark runners."""

  @abc.abstractmethod
  async def run_benchmark(
      self, benchmark_case: BenchmarkCaseT, generated_answer: GeneratedAnswer
  ) -> tuple[BenchmarkResultType, Optional[str], Optional[str], Optional[str]]:
    """Runs a benchmark and returns the result."""
    pass


class MultipleChoiceRunner(BenchmarkRunner[MultipleChoiceBenchmarkCase]):
  """Runs a multiple choice benchmark."""

  async def run_benchmark(
      self,
      benchmark_case: MultipleChoiceBenchmarkCase,
      generated_answer: GeneratedAnswer,
  ) -> tuple[BenchmarkResultType, Optional[str], Optional[str], Optional[str]]:
    """Checks if the answer matches the correct option."""
    answer = generated_answer.output.answer.strip().upper()
    correct = benchmark_case.correct_answer.strip().upper()

    if answer == correct:
      return BenchmarkResultType.PASS, None, None, None
    else:
      from benchmarks.data_models import BenchmarkErrorType

      return (
          BenchmarkResultType.FAIL_VALIDATION,
          (
              f"Expected '{correct}', but got '{answer}'.\nQuestion:"
              f" {benchmark_case.question}"
          ),
          None,
          BenchmarkErrorType.MODEL_INCORRECT_ANSWER,
      )


class PytestBenchmarkRunner(BenchmarkRunner[FixErrorBenchmarkCase]):
  """A benchmark runner that uses pytest to run the tests."""

  def _verify_signature(self, generated_code: str) -> Optional[str]:
    """Verifies that the generated function signature matches the standard."""
    try:
      try:
        tree = ast.parse(textwrap.dedent(generated_code))
      except SyntaxError as e:
        return f"Syntax error when parsing code for signature verification: {e}"

      # Find function def
      func_node = None
      for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "create_agent":
          func_node = node
          break

      if not func_node:
        return "Generated code does not define 'create_agent' function."

      # Verify args: (model_name: str)
      args = func_node.args.args
      if len(args) != 1:
        return f"Expected 1 argument 'model_name', got {len(args)}"

      arg = args[0]
      if arg.arg != "model_name":
        return f"Expected argument name 'model_name', got '{arg.arg}'"

      # Check annotation if present
      if arg.annotation:
        try:
          ann = ast.unparse(arg.annotation)
          if ann != "str":
            return f"Expected argument type 'str', got '{ann}'"
        except AttributeError:
          pass  # Python < 3.9

      # Verify return type: -> BaseAgent
      if func_node.returns:
        try:
          ret = ast.unparse(func_node.returns)
          if ret != "BaseAgent":
            return f"Expected return type 'BaseAgent', got '{ret}'"
        except AttributeError:
          pass
      else:
        return "Missing return type annotation '-> BaseAgent'"

      return None

    except (SyntaxError, AttributeError) as e:
      return f"Signature verification failed with internal error: {e}"

  async def run_benchmark(
      self,
      benchmark_case: FixErrorBenchmarkCase,
      generated_answer: GeneratedAnswer,
  ) -> tuple[BenchmarkResultType, str, str, Optional[str]]:
    """Runs a benchmark using pytest and returns the result and logs."""
    code_to_test = generated_answer.output.code
    project_root = Path(__file__).parent.parent

    # Create a temp directory for execution
    tmpdir = tempfile.mkdtemp(prefix="benchmark_")
    tmp_path = Path(tmpdir)

    # Helper to read file content
    def read_file(path: Path) -> str:
      if not path.exists():
        raise FileNotFoundError(f"Could not find file: {path}")
      with open(path, "r", encoding="utf-8") as f:
        return f.read()

    target_test_file = tmp_path / "test_temp.py"

    if benchmark_case.unfixed_file and benchmark_case.fixed_file:
      test_file_path = project_root / benchmark_case.test_file

      # Verify signature before proceeding.
      sig_error = self._verify_signature(code_to_test)
      if sig_error:
        from benchmarks.data_models import BenchmarkErrorType

        return (
            BenchmarkResultType.FAIL_VALIDATION,
            f"Signature Verification Failed:\n{sig_error}",
            None,
            BenchmarkErrorType.MODEL_ANSWER_DID_NOT_MATCH_TEMPLATE,
        )

      # 2. Write the generated code to 'fixed.py' in the temp dir (as candidate)
      (tmp_path / "fixed.py").write_text(code_to_test, encoding="utf-8")

      # 2b. Write the unfixed code to 'unfixed.py' in the temp dir
      unfixed_content = read_file(project_root / benchmark_case.unfixed_file)
      (tmp_path / "unfixed.py").write_text(unfixed_content, encoding="utf-8")

      # 3. Read and write the test file to the temp dir
      test_content = read_file(test_file_path)
      target_test_file.write_text(test_content, encoding="utf-8")

      # 4. Create __init__.py to make it a package (helps with relative imports)
      (tmp_path / "__init__.py").touch()

    elif benchmark_case.agent_file:  # Fallback for deprecated agent_file

      test_file_path = project_root / benchmark_case.test_file

      # Verify signature before proceeding (legacy check)
      sig_error = self._verify_signature(code_to_test)
      if sig_error:
        from benchmarks.data_models import BenchmarkErrorType

        return (
            BenchmarkResultType.FAIL_VALIDATION,
            f"Signature Verification Failed:\n{sig_error}",
            None,
            BenchmarkErrorType.MODEL_ANSWER_DID_NOT_MATCH_TEMPLATE,
        )

      # For deprecated agent_file, we assume the generated code is still only the agent definition,
      # and it needs to be injected into the original agent_file content.
      # However, since the prompt specifies the candidate should return the *entire* unfixed.py,
      # this legacy branch might become obsolete or need further adjustment.
      # For now, if this branch is hit, we treat `code_to_test` as the full agent file.
      (tmp_path / "agent.py").write_text(code_to_test, encoding="utf-8")

      # 3. Read and write test file
      test_content = read_file(test_file_path)
      target_test_file.write_text(test_content, encoding="utf-8")

      # 4. Create __init__.py to make it a package (helps with relative imports)
      (tmp_path / "__init__.py").touch()

    else:  # Legacy single-file mode with no agent_file explicitly set
      test_file_path = project_root / benchmark_case.test_file
      # In this legacy mode, code_to_test should contain the full file.
      target_test_file.write_text(code_to_test, encoding="utf-8")

    # Prepare environment with PYTHONPATH including the temp directory and project root
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH", "")
    # Add both tmp_path (for fixed.py/unfixed.py) and project_root (for benchmarks package)
    additional_paths = f"{str(tmp_path)}{os.pathsep}{str(project_root)}"
    if pythonpath:
      env["PYTHONPATH"] = f"{pythonpath}{os.pathsep}{additional_paths}"
    else:
      env["PYTHONPATH"] = additional_paths

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pytest",
        "--asyncio-mode=auto",
        "test_temp.py",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=str(tmp_path),
    )
    stdout, stderr = await proc.communicate()

    output_str = stdout.decode() + stderr.decode()

    logs = (
        f"--- Pytest stdout ---\n{stdout.decode()}\n"
        f"--- Pytest stderr ---\n{stderr.decode()}"
    )

    error_type = None
    result = BenchmarkResultType.FAIL_CRASH  # Default to crash if non-zero exit

    if proc.returncode == 0:
      result = BenchmarkResultType.PASS
    elif proc.returncode == 1:
      # Standard Python exception pattern in pytest output: "E   ExceptionName: message"
      # We look for the last occurrence of such pattern as it's usually the root cause.
      exception_match = re.search(r"E\s+([a-zA-Z0-9_.]*Error):", output_str)
      extracted_error_name = (
          exception_match.group(1) if exception_match else None
      )

      if extracted_error_name:
        # Map string to enum if possible
        try:
          # Attempt to match extracted name to enum value
          # (e.g. "NameError" -> BenchmarkErrorType.NAME_ERROR)
          # Since enum values are strings like "NameError", we can check values.
          from benchmarks.data_models import BenchmarkErrorType

          # Normalize: if extracted is "google.genai.errors.ClientError", take "ClientError"
          simple_name = extracted_error_name.split(".")[-1]

          # Try to find matching enum member by value
          found_member = None
          for member in BenchmarkErrorType:
            if member.value == simple_name:
              found_member = member
              break

          if found_member:
            error_type = found_member
          else:
            # Fallback for unmapped exceptions (still crash/fail but typed as Other)
            error_type = BenchmarkErrorType.OTHER_ERROR

        except (AttributeError, ValueError):
          error_type = BenchmarkErrorType.OTHER_ERROR
      else:
        # No explicit exception found
        from benchmarks.data_models import BenchmarkErrorType

        if "AssertionError" in output_str:
          error_type = BenchmarkErrorType.ASSERTION_ERROR
        elif "FAILED" in output_str:
          error_type = BenchmarkErrorType.TEST_FAILURE
        else:
          error_type = BenchmarkErrorType.OTHER_ERROR

      # Determine if it's a crash or validation failure based on the classified type
      from benchmarks.data_models import BenchmarkErrorType

      # Infrastructure/Crash types
      crash_types = {
          BenchmarkErrorType.CLIENT_ERROR,
          BenchmarkErrorType.SERVER_ERROR,
          BenchmarkErrorType.RESOURCE_EXHAUSTED,
          BenchmarkErrorType.TIMEOUT_ERROR,
          BenchmarkErrorType.CONNECTION_ERROR,
          BenchmarkErrorType.SYSTEM_EXIT,
          BenchmarkErrorType.SYNTAX_ERROR,
          BenchmarkErrorType.INDENTATION_ERROR,
          BenchmarkErrorType.IMPORT_ERROR,
          BenchmarkErrorType.MODULE_NOT_FOUND_ERROR,
          BenchmarkErrorType.NAME_ERROR,  # Often user code crash
          BenchmarkErrorType.TYPE_ERROR,  # Often user code crash
          BenchmarkErrorType.ATTRIBUTE_ERROR,  # Often user code crash
      }

      if error_type in crash_types:
        result = BenchmarkResultType.FAIL_CRASH
      else:
        # Assertion failures and generic test failures are validation issues
        result = BenchmarkResultType.FAIL_VALIDATION

    else:
      # Return codes > 1 usually indicate usage errors or internal errors
      from benchmarks.data_models import BenchmarkErrorType

      result = BenchmarkResultType.FAIL_CRASH
      error_type = BenchmarkErrorType.SYSTEM_EXIT

    return result, logs, str(tmp_path), error_type


class ApiUnderstandingRunner(BenchmarkRunner[ApiUnderstandingBenchmarkCase]):
  """
  A benchmark runner that validates answers for API understanding.
  """

  def _normalize_code(self, code: str) -> str:
    """Normalizes code for comparison by collapsing whitespace to one space and stripping."""
    # Replace all whitespace sequences with a single space
    code = re.sub(r"\s+", " ", code)
    # Remove leading/trailing whitespace
    return code.strip()

  async def run_benchmark(
      self,
      benchmark_case: ApiUnderstandingBenchmarkCase,
      generated_answer: GeneratedAnswer,
  ) -> tuple[BenchmarkResultType, str, None, Optional[str]]:
    """Validates the generated answer and returns the result and logs."""
    all_errors = []
    output = generated_answer.output
    code_to_test = output.code

    for ground_truth in benchmark_case.answers:
      try:
        validation_utils.validate_answer_against_template(
            code_to_test, benchmark_case.template
        )
        normalized_code = self._normalize_code(code_to_test)
        normalized_ground_truth = self._normalize_code(ground_truth.answer)
        if normalized_ground_truth not in normalized_code:
          raise validation_utils.ValidationError(
              "Normalized code does not match normalized ground truth."
          )
        validation_utils.validate_module_path(
            fully_qualified_class_name=generated_answer.output.fully_qualified_class_name,
            expected_paths=ground_truth.fully_qualified_class_name,
        )
        return BenchmarkResultType.PASS, "Validation successful.", None, None

      except validation_utils.ValidationError as e:
        all_errors.append(
            f"  - Ground Truth '{self._normalize_code(ground_truth.answer)}'"
            f" failed: {e}"
        )

    logs = (
        f"--- Validation Failed for: {benchmark_case.get_identifier()} ---\n"
        + "\n".join(all_errors)
    )
    # "ModelValidationError" indicates the generated code failed static or dynamic validation checks
    # (e.g. mismatched template, wrong class path) despite being syntactically valid.
    from benchmarks.data_models import BenchmarkErrorType

    return (
        BenchmarkResultType.FAIL_VALIDATION,
        logs,
        None,
        BenchmarkErrorType.MODEL_ANSWER_DID_NOT_MATCH_TEMPLATE,
    )
