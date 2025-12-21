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

"""Script to run benchmarks and analyze results."""

import asyncio
import json
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import sys
import argparse

# Add root to sys.path if not there
if str(Path.cwd()) not in sys.path:
    sys.path.append(str(Path.cwd()))

import pydantic
import pandas as pd

from benchmarks import benchmark_orchestrator
from benchmarks.benchmark_candidates import CANDIDATE_GENERATORS
from benchmarks.answer_generators.gemini_cli_docker import (
    GeminiCliPodmanAnswerGenerator, 
    GeminiCliCloudRunAnswerGenerator
)
from benchmarks.answer_generators.base import AnswerGenerator
from benchmarks.config import PODMAN_CONFIG
from benchmarks.data_models import BenchmarkRunResult
from benchmarks.logger import JsonTraceLogger
import benchmarks.analysis as analysis

# Set pandas display options (needed for analysis functions)
pd.set_option("display.max_colwidth", None)
pd.set_option("display.max_rows", None)


async def run_comparison(logger: JsonTraceLogger, selected_suite: Optional[str] = None) -> List[BenchmarkRunResult]:
  """Sets up and runs the benchmark comparison sequentially per generator."""
  print("Configuring benchmark run...")

  all_benchmark_suites = [
      "benchmarks/benchmark_definitions/api_understanding/benchmark.yaml",
      "benchmarks/benchmark_definitions/fix_errors/benchmark.yaml",
      "benchmarks/benchmark_definitions/diagnose_setup_errors_mc/benchmark.yaml",
      "benchmarks/benchmark_definitions/configure_adk_features_mc/benchmark.yaml",
      "benchmarks/benchmark_definitions/predict_runtime_behavior_mc/benchmark.yaml",
      "benchmarks/benchmark_definitions/debug_suite/benchmark.yaml", # Add the new debug suite
  ]

  if selected_suite:
      benchmark_suites = [s for s in all_benchmark_suites if selected_suite in s]
      if not benchmark_suites:
          raise ValueError(f"Specified suite '{selected_suite}' not found.")
  else:
      benchmark_suites = all_benchmark_suites

  answer_generators: list[AnswerGenerator] = CANDIDATE_GENERATORS

  print(f"Executing benchmarks with {len(answer_generators)} generators...")
  
  all_results = []

  for generator in answer_generators:
      print(f"\n--- Starting Generator: {generator.name} ---")
      
      try:
          print(f"[{generator.name}] Setting up...")
          await generator.setup()
        
          # Determine if we should use a proxy for the actual execution
          target_generator = generator
          
          # For Podman generators, create a lightweight proxy that points to the running container
          if isinstance(generator, GeminiCliPodmanAnswerGenerator):
              if hasattr(generator, "_base_url") and generator._base_url:
                  print(f"[{generator.name}] Creating proxy for execution at {generator._base_url}")
                  target_generator = GeminiCliPodmanAnswerGenerator(
                      dockerfile_dir=generator.dockerfile_dir,
                      image_name=generator.image_name,
                      image_definitions=generator._image_definitions,
                      model_name=generator.model_name,
                      context_instruction=generator.context_instruction,
                      service_url=generator._base_url
                  )

          # For Cloud Run generators, create a lightweight proxy that points to the deployed service
          elif isinstance(generator, GeminiCliCloudRunAnswerGenerator):
              if hasattr(generator, "service_url") and generator.service_url:
                  print(f"[{generator.name}] Creating proxy for execution at {generator.service_url}")
                  target_generator = GeminiCliCloudRunAnswerGenerator(
                      dockerfile_dir=generator.dockerfile_dir,
                      service_name=generator.service_name,
                      project_id=generator.project_id,
                      region=generator.region,
                      model_name=generator.model_name,
                      context_instruction=generator.context_instruction,
                      service_url=generator.service_url,
                      image_name=generator.image_name
                  )

          results = await benchmark_orchestrator.run_benchmarks(
              benchmark_suites=benchmark_suites,
              answer_generators=[target_generator], 
              max_concurrency=PODMAN_CONFIG.MAX_GLOBAL_CONCURRENCY,
              max_retries=2,
              logger=logger,
          )
          all_results.extend(results)
      
      except Exception as e:
          print(f"[{generator.name}] Error during execution: {e}")
      
      finally:
          print(f"[{generator.name}] Tearing down...")
          await generator.teardown()

  return all_results


async def main():
  """Main function to run benchmarks and analyze results."""
  parser = argparse.ArgumentParser(description="Run benchmarks against various answer generators.")
  parser.add_argument("--suite", type=str, help="Run only benchmarks from a specific suite (e.g., 'fix_errors').")
  args = parser.parse_args()

  # Setup unified output directory
  run_output_dir_str = os.environ.get("BENCHMARK_OUTPUT_DIR")
  if run_output_dir_str:
    run_output_dir = Path(run_output_dir_str)
  else:
    current_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_output_dir = Path("benchmark_runs") / current_timestamp

  run_output_dir.mkdir(parents=True, exist_ok=True)

  # Initialize logger
  logger = JsonTraceLogger(output_dir=str(run_output_dir), filename="trace.jsonl")

  # Execute the benchmarks
  benchmark_run_results = await run_comparison(logger=logger, selected_suite=args.suite)

  # Save raw results to JSON for later visualization
  results_json_path = run_output_dir / "results.json"
  TypeAdapter = pydantic.TypeAdapter(List[BenchmarkRunResult])
  with open(results_json_path, "w", encoding="utf-8") as f:
      f.write(TypeAdapter.dump_json(benchmark_run_results, indent=2).decode("utf-8"))
  print(f"Raw benchmark results saved to: {results_json_path}")

  logger.finalize_run()

if __name__ == "__main__":
  asyncio.run(main())
