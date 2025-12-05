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

"""Integration test for the benchmark orchestrator."""

import pandas as pd
import pytest

from benchmarks import benchmark_orchestrator
from benchmarks.answer_generators import GroundTruthAnswerGenerator


@pytest.mark.asyncio
async def test_benchmark_orchestrator_integration():
  """
  Runs an integration test for the benchmark orchestrator.

  This test runs a small subset of the benchmarks against the
  GroundTruthAnswerGenerator to ensure the end-to-end orchestration pipeline
  is working correctly.
  """
  benchmark_suites = [
      "benchmarks/benchmark_definitions/fix_errors/benchmark.yaml",
      "benchmarks/benchmark_definitions/configure_adk_features_mc/benchmark.yaml",
  ]

  answer_generators = [GroundTruthAnswerGenerator()]

  results = await benchmark_orchestrator.run_benchmarks(
      benchmark_suites, answer_generators, max_retries=0
  )

  assert results, "The benchmark run should produce results."

  raw_results_df = pd.DataFrame([r.model_dump() for r in results])

  summary_df = (
      raw_results_df.groupby("answer_generator")["result"]
      .agg(["sum", "count"])
      .rename(columns={"sum": "passed", "count": "total"})
  )
  summary_df["pass_rate"] = summary_df["passed"] / summary_df["total"]

  print("\n--- Orchestrator Integration Test Summary ---")
  print(summary_df)

  pass_rate = summary_df.loc["GroundTruthAnswerGenerator"]["pass_rate"]

  # Assert that the pass rate for the ground truth is high, allowing for a
  # small margin of error in case some ground truth answers become outdated.
  assert (
      pass_rate > 0.75
  ), "GroundTruthAnswerGenerator should achieve a high pass rate."
