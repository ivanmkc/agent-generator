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

"""Integration tests for GeminiCliAnswerGenerator without mocking."""

import asyncio
import json
from pathlib import Path

import pytest

from benchmarks.answer_generators.gemini_cli_answer_generator import (
    GeminiCliAnswerGenerator,
)
from benchmarks.benchmark_runner import PytestBenchmarkRunner
from benchmarks.data_models import AnswerTemplate
from benchmarks.data_models import ApiUnderstandingBenchmarkCase
from benchmarks.data_models import BenchmarkType
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.data_models import StringMatchAnswer
from benchmarks.data_models import TraceLogEvent
from benchmarks.tests.integration.predefined_cases import CONCURRENCY_TEST_CASE
from benchmarks.tests.integration.predefined_cases import (
    FIX_ERROR_MINIMAL_AGENT_CONTENT,
)
from benchmarks.tests.integration.predefined_cases import GEMINI_CLI_MC_CASE
from benchmarks.tests.integration.predefined_cases import SIMPLE_API_UNDERSTANDING_CASE
from benchmarks.tests.integration.test_utils import setup_fix_error_case

# Ensure the test file path is relative to the project root as expected by the runner
TEST_FIX_ERROR_FILE_PATH = Path(
    "benchmarks/benchmark_definitions/fix_errors/cases/01_single_llm_agent/test_agent.py"
)
UNFIXED_FILE_PATH = Path(
    "benchmarks/benchmark_definitions/fix_errors/cases/01_single_llm_agent/unfixed.py"
)
FIXED_FILE_PATH = Path(
    "benchmarks/benchmark_definitions/fix_errors/cases/01_single_llm_agent/fixed.py"
)


@pytest.mark.parametrize("case", [SIMPLE_API_UNDERSTANDING_CASE])
@pytest.mark.asyncio
async def test_gemini_cli_generator_simple_api_understanding(
    case: ApiUnderstandingBenchmarkCase,
):
  """
  Tests the GeminiCliAnswerGenerator with a real API Understanding case.
  We use a trivial question to ensure the test passes reliably if the integration works.
  """
  # Use flash model for speed and cost in tests
  generator = GeminiCliAnswerGenerator(model_name="gemini-2.5-flash")

  try:
    generated_answer = await generator.generate_answer(case)

    # Verify structure
    assert generated_answer.output.code, "Code should not be empty"
    assert (
        generated_answer.output.fully_qualified_class_name
    ), "FQN should not be empty"
    assert generated_answer.output.rationale, "Rationale should not be empty"

    # Verify content correctness (Checking for the requested trivial output)
    assert (
        "Event" in generated_answer.output.fully_qualified_class_name
    ), "FQN missing 'Event'"
    assert "Event" in generated_answer.output.code, "Code missing 'Event'"

    # Verify trace logs
    assert generated_answer.trace_logs, "Trace logs should not be empty"
    assert all(
        isinstance(log_entry, TraceLogEvent)
        for log_entry in generated_answer.trace_logs
    ), "All trace log entries should be TraceLogEvent objects"
    assert any(
        log_entry.type in ("message", "system_result")
        for log_entry in generated_answer.trace_logs
    ), "Trace logs should contain 'message' or 'system_result' entries"

  except Exception as e:
    pytest.fail(f"GeminiCliAnswerGenerator integration test failed: {e}")


@pytest.mark.parametrize("case", [GEMINI_CLI_MC_CASE])
@pytest.mark.asyncio
async def test_gemini_cli_generator_multiple_choice(
    case: MultipleChoiceBenchmarkCase,
):
  """
  Tests the GeminiCliAnswerGenerator with a MultipleChoiceBenchmarkCase.
  We use a trivial question to ensure the test passes reliably.
  """
  generator = GeminiCliAnswerGenerator(model_name="gemini-2.5-flash")

  try:
    generated_answer = await generator.generate_answer(case)

    # Check the answer
    assert (
        generated_answer.output.answer == "B"
    ), f"Expected answer 'B', got '{generated_answer.output.answer}'"

    # Check rationale exists
    assert generated_answer.output.rationale, "Rationale should not be empty"

    # Check trace logs
    assert generated_answer.trace_logs, "Trace logs should not be empty"
    assert all(
        isinstance(log_entry, TraceLogEvent)
        for log_entry in generated_answer.trace_logs
    ), "All trace log entries should be TraceLogEvent objects"
    assert any(
        log_entry.type in ("message", "system_result")
        for log_entry in generated_answer.trace_logs
    ), "Trace logs should contain 'message' or 'system_result' entries"

  except Exception as e:
    pytest.fail(f"Gemini CLI generator MC benchmark failed: {e}")


@pytest.mark.parametrize("fix_error_content", [FIX_ERROR_MINIMAL_AGENT_CONTENT])
@pytest.mark.asyncio
async def test_gemini_cli_generator_fix_error(tmp_path, fix_error_content):
  """
  Tests the GeminiCliAnswerGenerator with the '01: A minimal LlmAgent' fix_error case.
  We provide the exact solution code in the requirements to ensure the test passes.
  """
  generator = GeminiCliAnswerGenerator(model_name="gemini-2.5-flash")

  case = setup_fix_error_case(tmp_path, fix_error_content)

  try:
    # 1. Generate the answer (code fix)
    generated_answer = await generator.generate_answer(case)

    # Check trace logs
    assert generated_answer.trace_logs, "Trace logs should not be empty"
    assert all(
        isinstance(log_entry, TraceLogEvent)
        for log_entry in generated_answer.trace_logs
    ), "All trace log entries should be TraceLogEvent objects"
    assert any(
        log_entry.type in ("message", "system_result")
        for log_entry in generated_answer.trace_logs
    ), "Trace logs should contain 'message' or 'system_result' entries"

    # 2. Verify the answer using the actual PytestBenchmarkRunner

    runner = PytestBenchmarkRunner()
    result, logs, temp_file, error_type = await runner.run_benchmark(
        case, generated_answer
    )

    # Assertions
    assert (
        result == "pass"
    ), f"Benchmark failed with result: {result}. Logs:\n{logs}"

  except Exception as e:
    pytest.fail(f"Gemini CLI generator fix_error integration test failed: {e}")


@pytest.mark.parametrize("case", [CONCURRENCY_TEST_CASE])
@pytest.mark.asyncio
async def test_gemini_cli_generator_concurrency(
    case: ApiUnderstandingBenchmarkCase,
):
  """
  Tests that the GeminiCliAnswerGenerator can handle concurrent requests.
  This ensures the subprocess execution doesn't lock up or fail under load.
  """
  generator = GeminiCliAnswerGenerator(model_name="gemini-2.5-flash")
  concurrency_level = 5

  async def run_one():
    try:
      await generator.generate_answer(case)
    except Exception as e:
      pytest.fail(f"Concurrent run failed for {generator.name}: {e}")

  tasks = [run_one() for _ in range(concurrency_level)]
  await asyncio.gather(*tasks)
