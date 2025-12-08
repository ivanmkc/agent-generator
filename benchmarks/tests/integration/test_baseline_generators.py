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

"""Integration tests for Baseline Answer Generators (Ground Truth and Trivial)."""

import pandas as pd
import pytest

from benchmarks import benchmark_orchestrator
from benchmarks.answer_generators import GroundTruthAnswerGenerator
from benchmarks.answer_generators import TrivialAnswerGenerator


@pytest.mark.asyncio
async def test_benchmarks():
  """
  Runs a comprehensive benchmark test suite against baseline generators.

  This test evaluates:
  1. GroundTruthAnswerGenerator: Must achieve a perfect score (100% pass rate) to
     validate the integrity of the benchmark definitions and runner logic.
  2. TrivialAnswerGenerator: Must achieve a low score (sanity check) to ensure
     benchmarks are not trivially solvable by random/empty answers.
  """
  benchmark_suites = [
      "benchmarks/benchmark_definitions/api_understanding/benchmark.yaml",
      "benchmarks/benchmark_definitions/fix_errors/benchmark.yaml",
      "benchmarks/benchmark_definitions/diagnose_setup_errors_mc/benchmark.yaml",
      "benchmarks/benchmark_definitions/configure_adk_features_mc/benchmark.yaml",
      "benchmarks/benchmark_definitions/predict_runtime_behavior_mc/benchmark.yaml",
  ]
  answer_generators = [GroundTruthAnswerGenerator(), TrivialAnswerGenerator()]
  results = await benchmark_orchestrator.run_benchmarks(
      benchmark_suites, answer_generators, max_retries=0
  )
  raw_results_df = pd.DataFrame([r.model_dump() for r in results])

  # Calculate summary from raw results
  summary_df = (
      raw_results_df.groupby("answer_generator")["result"]
      .agg(["sum", "count"])
      .rename(columns={"sum": "passed", "count": "total"})
  )
  summary_df["pass_rate"] = summary_df["passed"] / summary_df["total"]

  print("\n--- Benchmark Summary ---")
  print(summary_df)

  # Filter for GroundTruthAnswerGenerator results to check its pass rate.
  ground_truth_results_df = raw_results_df[
      raw_results_df["answer_generator"] == "GroundTruthAnswerGenerator"
  ]
  ground_truth_summary_df = (
      ground_truth_results_df.groupby("answer_generator")["result"]
      .agg(["sum", "count"])
      .rename(columns={"sum": "passed", "count": "total"})
  )
  ground_truth_summary_df["pass_rate"] = (
      ground_truth_summary_df["passed"] / ground_truth_summary_df["total"]
  )

  # Debug: Print failures for GroundTruthAnswerGenerator
  failed_ground_truth = ground_truth_results_df[
      ground_truth_results_df["result"] == 0
  ]
  if not failed_ground_truth.empty:
    print("\n--- GroundTruthAnswerGenerator Failures ---")
    for _, row in failed_ground_truth.iterrows():
      print(f"Suite: {row['suite']}")
      print(f"Benchmark: {row['benchmark_name']}")
      print(f"Answer: {row['answer']}")
      print(f"Error: {row['validation_error']}")
      print("-" * 20)

    ground_truth_pass_rate = ground_truth_summary_df.loc[
        "GroundTruthAnswerGenerator"
    ]["pass_rate"]
    assert (
        ground_truth_pass_rate == 1.0
    ), "GroundTruthAnswerGenerator failed to achieve a perfect score."

    # Also verify that TrivialAnswerGenerator has a low pass rate (sanity check).
    trivial_summary = summary_df.loc["TrivialAnswerGenerator"]
    trivial_pass_rate = trivial_summary["pass_rate"]
    assert (
        trivial_pass_rate < 0.25
    ), "TrivialAnswerGenerator achieved a surprisingly high score."
