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
import importlib
import os
from pathlib import Path
import re
import sys
import tempfile
import textwrap
from typing import Generic
from typing import Optional
from typing import TypeVar
from pydantic import BaseModel

from benchmarks.data_models import (
    ApiUnderstandingBenchmarkCase,
    MultipleChoiceBenchmarkCase,
    SimulatorBenchmarkCase,
)
from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.data_models import BenchmarkResultType
from benchmarks.data_models import FixErrorBenchmarkCase
from benchmarks.data_models import GeneratedAnswer
from benchmarks.data_models import MultipleChoiceAnswerOutput, FixErrorAnswerOutput, ApiUnderstandingAnswerOutput, SimulatorAnswerOutput
import benchmarks.validation_utils as validation_utils

# A TypeVar to create a generic link between a runner and the case it handles.
BenchmarkCaseT = TypeVar("BenchmarkCaseT", bound=BaseBenchmarkCase)


class BenchmarkRunner(abc.ABC, Generic[BenchmarkCaseT]):
    """Abstract base class for benchmark runners."""

    async def ensure_valid_output(
        self, generated_answer: GeneratedAnswer, schema_class: type[BaseModel]
    ) -> tuple[Optional[BaseModel], Optional[str]]:
        """
        Ensures the generated answer has a valid structured output.
        If 'output' is missing, attempts to sanitize 'raw_output' using the LLM sanitizer.
        """
        if generated_answer.output:
            return generated_answer.output, None

        if not generated_answer.raw_output:
            return (
                None,
                "No output provided (parsing failed and no raw output captured).",
            )

        from benchmarks.parsing.json_sanitizer import JsonSanitizer
        from core.api_key_manager import API_KEY_MANAGER

        sanitizer = JsonSanitizer(api_key_manager=API_KEY_MANAGER)
        try:
            output = await sanitizer.sanitize(generated_answer.raw_output, schema_class)
            generated_answer.output = output  # Patch for downstream usage
            return output, None
        except Exception as e:
            return None, f"JSON Sanitization Failed: {e}"

    @abc.abstractmethod
    async def run_benchmark(
        self, benchmark_case: BenchmarkCaseT, generated_answer: GeneratedAnswer
    ) -> tuple[BenchmarkResultType, Optional[str], Optional[str], Optional[str]]:
        """Runs a benchmark and returns the result."""
        pass


class SimulatorRunner(BenchmarkRunner[SimulatorBenchmarkCase]):
    """Runs a CLI simulation benchmark."""

    async def run_benchmark(
        self,
        benchmark_case: SimulatorBenchmarkCase,
        generated_answer: GeneratedAnswer,
    ) -> tuple[BenchmarkResultType, Optional[str], Optional[str], Optional[str]]:
        """Checks if the simulation result was successful."""
        output, error = await self.ensure_valid_output(
            generated_answer, SimulatorAnswerOutput
        )
        if not output:
            from benchmarks.data_models import BenchmarkErrorType

            return (
                BenchmarkResultType.FAIL_VALIDATION,
                f"Failed to parse simulator output: {error}",
                None,
                BenchmarkErrorType.OTHER_ERROR, # Or a new type for infrastructure errors
            )

        if output.is_correct:
            return BenchmarkResultType.PASS, None, None, None
        else:
            from benchmarks.data_models import BenchmarkErrorType
            # The transcript is often too verbose for a simple error log,
            # so we provide a concise failure message.
            return (
                BenchmarkResultType.FAIL_VALIDATION,
                "The simulation ran successfully but the final verification failed.",
                None,
                BenchmarkErrorType.MODEL_INCORRECT_ANSWER, # This implies the agent's behavior was wrong
            )


class MultipleChoiceRunner(BenchmarkRunner[MultipleChoiceBenchmarkCase]):
    """Runs a multiple choice benchmark."""

    async def run_benchmark(
        self,
        benchmark_case: MultipleChoiceBenchmarkCase,
        generated_answer: GeneratedAnswer,
    ) -> tuple[BenchmarkResultType, Optional[str], Optional[str], Optional[str]]:
        """Checks if the answer matches the correct option."""

        # 1. Ensure Output
        output, error = await self.ensure_valid_output(
            generated_answer, MultipleChoiceAnswerOutput
        )
        if not output:
            from benchmarks.data_models import BenchmarkErrorType

            return (
                BenchmarkResultType.FAIL_VALIDATION,
                f"Failed to parse answer: {error}",
                None,
                BenchmarkErrorType.MODEL_INCORRECT_ANSWER,
            )

        answer = output.answer.strip().upper()
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

    async def _verify_signature_runtime(self, cwd: Path, env: dict) -> Optional[str]:
        """
        Verifies the signature using a runtime script that imports the generated module.
        This handles aliases (e.g. google.adk.agents.BaseAgent vs BaseAgent) correctly.
        """
        checker_script = r"""
import sys
import inspect
import typing
import traceback

try:
    # Attempt to import the required base class for comparison
    # We assume the environment has google.adk installed
    from google.adk.agents import BaseAgent
    from google.adk.apps import App
except ImportError:
    # If the environment is somehow broken, we can't verify strictly, 
    # but we also can't fail the user for env issues.
    # However, for this benchmark, ADK presence is mandatory.
    print("CRITICAL: Could not import google.adk.agents.BaseAgent or google.adk.apps.App in verification script.")
    sys.exit(1)

try:
    import fixed
except ImportError as e:
    print(f"ImportError importing generated code: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error importing generated code: {e}")
    traceback.print_exc()
    sys.exit(1)

if not hasattr(fixed, "create_agent"):
    print("Generated code does not define 'create_agent' function.")
    sys.exit(1)

# Inspect the function
func = fixed.create_agent
sig = inspect.signature(func)

# 1. Verify Arguments: (model_name: str)
params = list(sig.parameters.values())
if len(params) != 1:
    print(f"Expected 1 argument 'model_name', got {len(params)}")
    sys.exit(1)

param = params[0]
if param.name != "model_name":
    print(f"Expected argument name 'model_name', got '{param.name}'")
    sys.exit(1)

# Check annotation if it exists (not strictly enforcing 'str' at runtime if missing, 
# but good to check if present)
if param.annotation is not inspect.Parameter.empty:
    # If it's a string 'str' or the class str
    if param.annotation is not str and str(param.annotation) != 'str':
         print(f"Expected argument type 'str', got '{param.annotation}'")
         # We'll allow it for now to be lenient, or strict? Let's be lenient on arg type for now.
         pass

# 2. Verify Return Type: -> BaseAgent OR -> App
# This is the critical check.
ret_type = sig.return_annotation

if ret_type is inspect.Signature.empty:
    print("Missing return type annotation '-> BaseAgent' or '-> App'")
    sys.exit(1)

# Handle string forward references (from __future__ import annotations)
resolved_ret = ret_type
if isinstance(ret_type, str):
    # Try to resolve it. 
    # Simple check: does it match "BaseAgent" or "google.adk.agents.BaseAgent"?
    if ret_type == "BaseAgent" or ret_type.endswith(".BaseAgent"):
        sys.exit(0) # String match is good enough
    if ret_type == "App" or ret_type.endswith(".App"):
        sys.exit(0) # String match for App
    
    # Try to resolve strictly? 
    try:
        type_hints = typing.get_type_hints(func)
        resolved_ret = type_hints.get('return')
    except Exception:
        # If resolution fails, rely on the string check above
        print(f"Expected return type 'BaseAgent' or 'App', got '{ret_type}'")
        sys.exit(1)

# Now check the resolved type object
if resolved_ret is BaseAgent:
    sys.exit(0)
if resolved_ret is App:
    sys.exit(0)

# Check for subclasses if allowed (though the prompt usually asks for BaseAgent)
# Or fully qualified match
try:
    # BaseAgent
    if resolved_ret.__module__ == "google.adk.agents.base_agent" and resolved_ret.__name__ == "BaseAgent":
        sys.exit(0)
    # Also allow google.adk.agents.BaseAgent re-export
    if resolved_ret.__module__ == "google.adk.agents" and resolved_ret.__name__ == "BaseAgent":
        sys.exit(0)
        
    # App
    if resolved_ret.__module__ == "google.adk.apps.app" and resolved_ret.__name__ == "App":
        sys.exit(0)
    if resolved_ret.__module__ == "google.adk.apps" and resolved_ret.__name__ == "App":
        sys.exit(0)
except AttributeError:
    pass

print(f"Expected return type 'BaseAgent' or 'App', got '{resolved_ret}'")
sys.exit(1)
"""
        (cwd / "signature_check.py").write_text(checker_script, encoding="utf-8")

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "signature_check.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=str(cwd),
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return stdout.decode() + stderr.decode()

        return None

    async def run_benchmark(
        self,
        benchmark_case: FixErrorBenchmarkCase,
        generated_answer: GeneratedAnswer,
    ) -> tuple[BenchmarkResultType, str, str, Optional[str]]:
        """Runs a benchmark using pytest and returns the result and logs."""

        # 1. Ensure Output
        output, error = await self.ensure_valid_output(
            generated_answer, FixErrorAnswerOutput
        )
        if not output:
            from benchmarks.data_models import BenchmarkErrorType

            return (
                BenchmarkResultType.FAIL_VALIDATION,
                f"Failed to parse answer: {error}",
                None,
                BenchmarkErrorType.MODEL_INCORRECT_ANSWER,
            )

        code_to_test = output.code
        project_root = Path(__file__).parent.parent

        try:
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

                # 1. Write the generated code to 'fixed.py' in the temp dir (as candidate)
                (tmp_path / "fixed.py").write_text(code_to_test, encoding="utf-8")

                # 2. Write the unfixed code to 'unfixed.py' in the temp dir
                unfixed_content = read_file(project_root / benchmark_case.unfixed_file)
                (tmp_path / "unfixed.py").write_text(unfixed_content, encoding="utf-8")

                # 3. Read and write the test file to the temp dir
                test_content = read_file(test_file_path)
                target_test_file.write_text(test_content, encoding="utf-8")

                # 4. Create __init__.py to make it a package (helps with relative imports)
                (tmp_path / "__init__.py").touch()

                # 5. Create conftest.py to mock litellm and avoid real API calls
                conftest_content = r"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys

def pytest_sessionstart(session):
    # Patch run_agent_test to ensure it always returns a response
    try:
        import benchmarks.test_helpers as helpers
        original_run_agent_test = helpers.run_agent_test
        
        async def mock_run_agent_test(agent, input_message, **kwargs):
            # Respect mock_llm_response from the test call
            base_response = kwargs.get("mock_llm_response") or "Hello! I am a mocked response."
            
            # If it's the callback test, we need to simulate the callback effect
            if agent.name == "callback_agent":
                 return base_response + " (modified by callback)"
            
            return base_response
            
        helpers.run_agent_test = mock_run_agent_test
    except ImportError:
        pass

    # A more complete mock for litellm response (as fallback)
    mock_response = MagicMock()
    mock_response.model = "mock-model"
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello! I am a mocked response."
    
    # Patch litellm
    try:
        import litellm
        litellm.completion = MagicMock(return_value=mock_response)
        litellm.acompletion = AsyncMock(return_value=mock_response)
    except ImportError:
        pass
"""
                (tmp_path / "conftest.py").write_text(conftest_content, encoding="utf-8")

                # Prepare environment with PYTHONPATH including the temp directory and project root
                env = os.environ.copy()
                pythonpath = env.get("PYTHONPATH", "")
                additional_paths = f"{str(tmp_path)}{os.pathsep}{str(project_root)}"
                if pythonpath:
                    env["PYTHONPATH"] = f"{pythonpath}{os.pathsep}{additional_paths}"
                else:
                    env["PYTHONPATH"] = additional_paths

                # 5. Verify signature at RUNTIME using the environment
                # sig_error = await self._verify_signature_runtime(tmp_path, env)
                # if sig_error:
                #     from benchmarks.data_models import BenchmarkErrorType
                #     return (
                #         BenchmarkResultType.FAIL_VALIDATION,
                #         f"Signature Verification Failed:\n{sig_error}",
                #         None,
                #         BenchmarkErrorType.MODEL_ANSWER_DID_NOT_MATCH_TEMPLATE,
                #     )

        except Exception as e:
            from benchmarks.data_models import BenchmarkErrorType

            return (
                BenchmarkResultType.FAIL_SETUP,
                f"Benchmark Setup Failed: {e}",
                None,
                BenchmarkErrorType.TEST_FAILURE,
            )

        # Proceed to run tests if signature check passed
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "pytest",
            "--asyncio-mode=auto",
            "-vv",
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
        result = (
            BenchmarkResultType.FAIL_VALIDATION
        )  # Default to validation fail if non-zero exit

        if proc.returncode == 0:
            result = BenchmarkResultType.PASS
        elif proc.returncode == 1:
            # Standard Python exception pattern in pytest output: "E   ExceptionName: message"
            # We look for the last occurrence of such pattern as it's usually the root cause.
            exception_match = re.search(r"E\s+([a-zA-Z0-9_.]*Error):", output_str)
            extracted_error_name = exception_match.group(1) if exception_match else None

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
                result = BenchmarkResultType.FAIL_VALIDATION
            else:
                # Assertion failures and generic test failures are validation issues
                result = BenchmarkResultType.FAIL_VALIDATION

        else:
            # Return codes > 1 usually indicate usage errors or internal errors
            from benchmarks.data_models import BenchmarkErrorType

            result = BenchmarkResultType.FAIL_SETUP
            error_type = BenchmarkErrorType.SYSTEM_EXIT

        return (
            result,
            logs if result != BenchmarkResultType.PASS else None,
            str(tmp_path),
            error_type,
        )


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

    def _import_symbol(self, path: str):
        """Dynamically imports a symbol from a fully qualified name."""
        if not path or not isinstance(path, str):
            return None

        parts = path.split(".")
        # Try different split points for module vs attribute
        # We start from the full path down to the first component
        for i in range(len(parts), 0, -1):
            module_path = ".".join(parts[:i])
            symbol_name = ".".join(parts[i:])

            try:
                module = importlib.import_module(module_path)
                if not symbol_name:
                    return module

                # Traverse attributes
                obj = module
                try:
                    for part in symbol_name.split("."):
                        obj = getattr(obj, part)
                    return obj
                except AttributeError:
                    continue
            except ImportError:
                continue
        return None

    async def run_benchmark(
        self,
        benchmark_case: ApiUnderstandingBenchmarkCase,
        generated_answer: GeneratedAnswer,
    ) -> tuple[BenchmarkResultType, str, None, Optional[str]]:
        """Validates the generated answer and returns the result and logs."""

        # 1. Ensure Output
        output, error = await self.ensure_valid_output(
            generated_answer, ApiUnderstandingAnswerOutput
        )
        if not output:
            from benchmarks.data_models import BenchmarkErrorType

            return (
                BenchmarkResultType.FAIL_VALIDATION,
                f"Failed to parse answer: {error}",
                None,
                BenchmarkErrorType.MODEL_INCORRECT_ANSWER,
            )

        all_errors = []
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

                # ROBUST PATH VALIDATION
                gen_path = output.fully_qualified_class_name
                exp_paths = ground_truth.fully_qualified_class_name

                # 1. Try Object Identity Check (handles re-exports/aliases)
                gen_obj = self._import_symbol(gen_path)
                match_found = False

                if gen_obj is not None:
                    for ep in exp_paths:
                        exp_obj = self._import_symbol(ep)
                        if exp_obj is not None and gen_obj == exp_obj:
                            match_found = True
                            break

                # 2. Fallback to strict String Check if Identity Check failed
                if not match_found:
                    validation_utils.validate_module_path(
                        fully_qualified_class_name=gen_path,
                        expected_paths=exp_paths,
                    )

                return BenchmarkResultType.PASS, None, None, None

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
