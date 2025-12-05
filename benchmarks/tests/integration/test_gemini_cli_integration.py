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

from pathlib import Path

import pytest

from benchmarks.answer_generators.gemini_cli_answer_generator import (
    GeminiCliAnswerGenerator,
)
from benchmarks.data_models import AnswerTemplate
from benchmarks.data_models import ApiUnderstandingBenchmarkCase
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.data_models import StringMatchAnswer


@pytest.mark.asyncio
async def test_gemini_cli_simple_call():
  """
  Tests a simple prompt call to the Gemini CLI to ensure it can run and return a response.
  This bypasses the complex benchmark case structure to verify basic connectivity.
  """
  generator = GeminiCliAnswerGenerator(model_name="gemini-2.5-flash")

  # We use the internal _run_cli_command method to send a direct text prompt
  # effectively testing the "Basic Usage" of the CLI but with JSON output.
  prompt = "What is 2 + 2? Reply with just the number."

  try:
    cli_json_response, logs = await generator._run_cli_command(prompt)

    assert (
        "response" in cli_json_response
    ), "CLI output missing 'response' field"
    assert (
        "4" in cli_json_response["response"]
    ), f"Expected '4' in response, got: {cli_json_response['response']}"

    # Verify stats are present (indicating successful structured output)
    assert "stats" in cli_json_response

    # Also verify logs are present
    assert logs, "Logs should not be empty"
    assert any(
        log_entry.type in ("message", "system_result") for log_entry in logs
    ), "Logs should contain 'message' or 'system_result' entries"

  except RuntimeError as e:
    pytest.fail(f"Gemini CLI integration test failed: {e}")


@pytest.mark.asyncio
async def test_gemini_cli_mc_benchmark_case():
  """
  Tests the GeminiCliAnswerGenerator with a MultipleChoiceBenchmarkCase.
  This verifies the end-to-end flow including prompt construction, CLI execution,
  and response parsing into the Pydantic model.
  """
  generator = GeminiCliAnswerGenerator(model_name="gemini-2.5-flash")

  case = MultipleChoiceBenchmarkCase(
      question="Which planet is known as the Red Planet?",
      options={"A": "Venus", "B": "Mars", "C": "Jupiter", "D": "Saturn"},
      correct_answer="B",
      benchmark_type="multiple_choice",
      explanation="Mars is the Red Planet.",
  )

  try:
    generated_answer = await generator.generate_answer(case)

    # Check the answer
    assert (
        generated_answer.output.answer == "B"
    ), f"Expected answer 'B', got '{generated_answer.output.answer}'"

    # Check rationale exists
    assert generated_answer.output.rationale, "Rationale should not be empty"

  except Exception as e:
    pytest.fail(f"Gemini CLI MC benchmark failed: {e}")
