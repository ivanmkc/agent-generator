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

"""
Integration test for the benchmark orchestrator's end-to-end execution flow.

DISTINCTION FROM `test_unified_generators.py`:
This test verifies the `benchmark_orchestrator` module (System Testing), whereas
`test_unified_generators.py` verifies individual `AnswerGenerator` implementations
(Component Testing).

Primary Goals:
1. Ensure the framework correctly loads benchmark definitions from YAML.
2. Verify the pipeline can dispatch tasks to multiple generators.
3. specific validation that the orchestrator aggregates results correctly.
4. Uses `GroundTruthAnswerGenerator` as a stable baseline to validate the
   framework mechanics without relying on stochastic LLM behavior.
"""

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


@pytest.mark.asyncio
async def test_benchmark_orchestrator_sequential_execution():
  """
  Verifies that generators are processed sequentially.
  """
  import time
  from benchmarks.answer_generators.base import AnswerGenerator
  from benchmarks.data_models import GeneratedAnswer, ApiUnderstandingAnswerOutput, BaseBenchmarkCase

  class MockAnswerGenerator(AnswerGenerator):
      def __init__(self, name):
          self._name = name
          self.setup_time = 0
          self.generation_times = []
          self.setup_called = 0

      @property
      def name(self) -> str:
          return self._name

      async def setup(self) -> None:
          self.setup_called += 1
          self.setup_time = time.time()
          await asyncio.sleep(0.1) # Simulate setup work

      async def generate_answer(
          self, benchmark_case: BaseBenchmarkCase
      ) -> GeneratedAnswer:
          self.generation_times.append(time.time())
          # Return a valid output that matches one of the types in the union (ApiUnderstandingAnswerOutput)
          output = ApiUnderstandingAnswerOutput(
              code="print('mock')",
              rationale="mock rationale",
              fully_qualified_class_name="mock.module.Class"
          )
          return GeneratedAnswer(output=output)

  gen1 = MockAnswerGenerator("gen1")
  gen2 = MockAnswerGenerator("gen2")

  # Use a small suite to run quickly
  benchmark_suites = [
      "benchmarks/benchmark_definitions/api_understanding/benchmark.yaml" 
  ]
  
  import asyncio
  await benchmark_orchestrator.run_benchmarks(
      benchmark_suites, [gen1, gen2], max_retries=0
  )

  assert gen1.setup_called == 1
  assert gen2.setup_called == 1

  # Verify Sequential Execution:
  # gen2.setup() should happen AFTER gen1 has finished its work.
  # Since we can't easily track "finished work" time from the outside without complex mocks,
  # checking that gen2.setup_time > gen1.generation_times[-1] is a good proxy.
  # This assumes gen1 had at least one task.
  
  if gen1.generation_times:
      last_gen1_activity = max(gen1.generation_times)
      assert gen2.setup_time > last_gen1_activity, (
          f"gen2 setup ({gen2.setup_time}) started before gen1 finished generation ({last_gen1_activity})"
      )

