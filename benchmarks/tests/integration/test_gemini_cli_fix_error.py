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

"""Integration tests for GeminiCliAnswerGenerator specifically for fix_error tasks."""

import asyncio
import os
from pathlib import Path

import pytest

from benchmarks.answer_generators.gemini_cli_answer_generator import (
    GeminiCliAnswerGenerator,
)
from benchmarks.benchmark_runner import PytestBenchmarkRunner
from benchmarks.tests.integration.test_utils import create_fix_error_benchmark_case

# Ensure the test file path is relative to the project root as expected by the runner
TEST_FILE_PATH = Path(
    "benchmarks/benchmark_definitions/fix_errors/cases/01_single_llm_agent/test_agent.py"
)
UNFIXED_FILE_PATH = Path(
    "benchmarks/benchmark_definitions/fix_errors/cases/01_single_llm_agent/unfixed.py"
)
FIXED_FILE_PATH = Path(
    "benchmarks/benchmark_definitions/fix_errors/cases/01_single_llm_agent/fixed.py"
)


@pytest.mark.asyncio
async def test_gemini_cli_fix_error_01(tmp_path):
  """
  Tests the GeminiCliAnswerGenerator with the '01: A minimal LlmAgent' fix_error case.
  This verifies the ability of the CLI + Model to generate code that fixes a test.
  """
  generator = GeminiCliAnswerGenerator(model_name="gemini-2.5-flash")

  test_file_path = tmp_path / "test_agent.py"
  unfixed_file_path = tmp_path / "unfixed.py"
  fixed_file_path = tmp_path / "fixed.py"

  test_file_path.write_text("def test_fixed(): pass")
  unfixed_file_path.write_text("def unfixed(): pass")
  fixed_file_path.write_text("def fixed(): pass")

  case = create_fix_error_benchmark_case(
      case_path=tmp_path,
      name="Test Fix Error",
      description="Fix a bug by creating a valid agent.",
      requirements=[
          (
              "The solution MUST import `BaseAgent` directly from"
              " `google.adk.agents`."
          ),
          (
              "The `create_agent` function MUST have the return type annotation"
              " `-> BaseAgent`."
          ),
      ],
  )

  try:
    # 1. Generate the answer (code fix)
    generated_answer = await generator.generate_answer(case)

    print(f"Generated Code:\n{generated_answer.output.code}")

    # 2. Verify the answer using the actual PytestBenchmarkRunner
    # This runs the generated code in a temporary file against the test logic
    runner = PytestBenchmarkRunner()
    result, logs, temp_file, error_type = await runner.run_benchmark(
        case, generated_answer
    )

    print(f"Runner Result: {result}")
    print(f"Runner Logs:\n{logs}")

    if error_type:
      print(f"Error Type: {error_type}")

    # Assertions
    # We assert that the result is PASS, meaning the CLI generated valid, working code
    # that passed the unit test defined in test_01_single_llm_agent.py
    assert (
        result == "pass"
    ), f"Benchmark failed with result: {result}. Logs:\n{logs}"

  except Exception as e:
    pytest.fail(f"Gemini CLI fix_error integration test failed: {e}")
