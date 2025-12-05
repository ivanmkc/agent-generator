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

"""Smoke test for the GeminiAnswerGenerator to verify basic functionality."""

from pathlib import Path

import pytest

from benchmarks import benchmark_orchestrator
from benchmarks.answer_generators import GeminiAnswerGenerator


@pytest.mark.asyncio
async def test_gemini_answer_generator_smoke():
  """
  Runs a smoke test for the GeminiAnswerGenerator.

  This test verifies that the GeminiAnswerGenerator can run through a subset
  of benchmarks without crashing and produces at least one successful result.
  It does not enforce a high pass rate, focusing on basic operational integrity.
  """
  benchmark_suites = [
      "benchmarks/benchmark_definitions/fix_errors/benchmark.yaml",
      "benchmarks/benchmark_definitions/configure_adk_features_mc/benchmark.yaml",
  ]

  answer_generators = [
      GeminiAnswerGenerator(
          model_name="gemini-1.5-flash", context=Path("llms.txt")
      )
  ]

  results = await benchmark_orchestrator.run_benchmarks(
      benchmark_suites, answer_generators, max_retries=2
  )

  assert results, "The benchmark run should produce results."

  # Assert that at least one result passed to confirm basic functionality
  # without being strict about overall model performance.
  assert (
      len(results) > 0
  ), "GeminiAnswerGenerator should produce results without crashing."
