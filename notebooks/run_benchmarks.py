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
    GeminiCliCloudRunAnswerGenerator,
)
from benchmarks.answer_generators.base import AnswerGenerator
from benchmarks.config import PODMAN_CONFIG
from benchmarks.data_models import BenchmarkRunResult
from benchmarks.logger import (
    JsonTraceLogger, 
    ConsoleBenchmarkLogger, 
    CompositeLogger
)
import benchmarks.analysis as analysis
from tools.log_analyzer import analyze_run_logs

# Set pandas display options (needed for analysis functions)
pd.set_option("display.max_colwidth", None)
pd.set_option("display.max_rows", None)


async def run_comparison(
    logger: CompositeLogger, 
    selected_suite: Optional[str] = None,
    selected_generator_filter: Optional[str] = None,
    selected_model_filter: Optional[str] = None,
    retry_on_validation_error: bool = False
) -> List[BenchmarkRunResult]:
    """Sets up and runs the benchmark comparison sequentially per generator."""
    logger.log_message("Configuring benchmark run...")

    debug_suite = "benchmarks/benchmark_definitions/debug_suite/benchmark.yaml"
    
    standard_suites = [
        "benchmarks/benchmark_definitions/api_understanding/benchmark.yaml",
        "benchmarks/benchmark_definitions/fix_errors/benchmark.yaml",
        #   "benchmarks/benchmark_definitions/diagnose_setup_errors_mc/benchmark.yaml",
        #   "benchmarks/benchmark_definitions/configure_adk_features_mc/benchmark.yaml",
        #   "benchmarks/benchmark_definitions/predict_runtime_behavior_mc/benchmark.yaml",
    ]

    if selected_suite == "debug":
        benchmark_suites = [debug_suite]
    elif selected_suite:
        # Allow filtering by name from all available suites
        all_suites = standard_suites + [debug_suite]
        benchmark_suites = [s for s in all_suites if selected_suite in s]
        if not benchmark_suites:
            raise ValueError(f"Specified suite filter '{selected_suite}' matched no suites.")
    else:
        # Default: Run all standard suites (exclude debug)
        benchmark_suites = standard_suites

    # Filter generators
    answer_generators: list[AnswerGenerator] = []
    
    # Start with all candidates
    answer_generators = CANDIDATE_GENERATORS
    
    # Filter by generator name
    if selected_generator_filter:
        answer_generators = [
            g for g in answer_generators 
            if selected_generator_filter.lower() in g.name.lower()
        ]
        
    # Filter by model name (if implemented on the generator)
    if selected_model_filter:
        filtered_by_model = []
        for g in answer_generators:
             # Most generators have a model_name attribute
             g_model = getattr(g, "model_name", "").lower()
             if selected_model_filter.lower() in g_model:
                 filtered_by_model.append(g)
        answer_generators = filtered_by_model

    if not answer_generators:
         logger.log_message(f"Warning: No generators matched the provided filters (gen: {selected_generator_filter}, model: {selected_model_filter}).")

    logger.log_message(f"Executing benchmarks with {len(answer_generators)} generators on {len(benchmark_suites)} suites...")

    all_results = []

    for generator in answer_generators:
        # Use logger section for the generator block
        with logger.section(f"Generator: {generator.name}"):
            
            # Filter suites based on generator compatibility
            current_suites = list(benchmark_suites)
            # TODO: Remove this filter when StructuredWorkflowAdk can adapt its output schema
            # to match different benchmark types (e.g., ApiUnderstanding). Currently, its FinalResponse
            # is hardcoded to FixErrorAnswerOutput.
            if "StructuredWorkflowAdk" in generator.name or "BaselineWorkflowAdk" in generator.name:
                 current_suites = [s for s in current_suites if "fix_errors" in s or "debug_suite" in s]
                 if not current_suites:
                     logger.log_message(f"Skipping: No compatible suites found (requires 'fix_errors').")
                     continue
                 logger.log_message(f"Restricted suites to: {current_suites}")

            try:
                logger.log_message(f"Running benchmarks on suites: {current_suites}")
                logger.log_message(f"Setting up...")
                await generator.setup()

                # Determine if we should use a proxy for the actual execution
                target_generator = generator

                # For Podman generators, create a lightweight proxy that points to the running container
                if isinstance(generator, GeminiCliPodmanAnswerGenerator):
                    if hasattr(generator, "_base_url") and generator._base_url:
                        logger.log_message(
                            f"Creating proxy for execution at {generator._base_url}"
                        )
                        target_generator = GeminiCliPodmanAnswerGenerator(
                            dockerfile_dir=generator.dockerfile_dir,
                            image_name=generator.image_name,
                            image_definitions=generator._image_definitions,
                            model_name=generator.model_name,
                            context_instruction=generator.context_instruction,
                            service_url=generator._base_url,
                        )

                # For Cloud Run generators, create a lightweight proxy that points to the deployed service
                elif isinstance(generator, GeminiCliCloudRunAnswerGenerator):
                    if hasattr(generator, "service_url") and generator.service_url:
                        logger.log_message(
                            f"Creating proxy for execution at {generator.service_url}"
                        )
                        target_generator = GeminiCliCloudRunAnswerGenerator(
                            dockerfile_dir=generator.dockerfile_dir,
                            service_name=generator.service_name,
                            project_id=generator.project_id,
                            region=generator.region,
                            model_name=generator.model_name,
                            context_instruction=generator.context_instruction,
                            service_url=generator.service_url,
                            image_name=generator.image_name,
                        )

                # Adjust concurrency for heavy generators
                concurrency = PODMAN_CONFIG.MAX_GLOBAL_CONCURRENCY

                # Note: run_benchmarks handles its own section logging for the execution
                results = await benchmark_orchestrator.run_benchmarks(
                    benchmark_suites=current_suites,
                    answer_generators=[target_generator],
                    max_concurrency=concurrency,
                    max_retries=2,
                    retry_on_validation_error=retry_on_validation_error,
                    logger=logger,
                )
                all_results.extend(results)

            except Exception as e:
                logger.log_message(f"Error during execution: {e}")

            finally:
                logger.log_message(f"Tearing down...")
                await generator.teardown()

    return all_results


async def main():
    """Main function to run benchmarks and analyze results."""
    parser = argparse.ArgumentParser(
        description="Run benchmarks against various answer generators."
    )
    parser.add_argument(
        "--suite-filter",
        type=str,
        help="Substring filter for benchmark suites (e.g., 'fix_errors', 'debug'). Default: All standard suites.",
    )
    parser.add_argument(
        "--generator-filter",
        type=str,
        help="Substring filter for generator names. Default: All candidates.",
    )
    parser.add_argument(
        "--model-filter",
        type=str,
        help="Substring filter for model names (e.g., 'flash', 'pro'). Default: All models.",
    )
    parser.add_argument(
        "--retry-on-validation-error",
        action="store_true",
        help="If set, retries generation upon validation errors (schema mismatch). Default: False.",
    )
    args = parser.parse_args()

    # Setup unified output directory
    run_output_dir_str = os.environ.get("BENCHMARK_OUTPUT_DIR")
    if run_output_dir_str:
        run_output_dir = Path(run_output_dir_str)
    else:
        current_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_output_dir = Path("benchmark_runs") / current_timestamp

    run_output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize loggers
    json_logger = JsonTraceLogger(output_dir=str(run_output_dir), filename="trace.jsonl")
    console_logger = ConsoleBenchmarkLogger()
    logger = CompositeLogger([console_logger, json_logger])

    # Execute the benchmarks
    benchmark_run_results = await run_comparison(
        logger=logger, 
        selected_suite=args.suite_filter,
        selected_generator_filter=args.generator_filter,
        selected_model_filter=args.model_filter,
        retry_on_validation_error=args.retry_on_validation_error
    )

    # Save raw results to JSON for later visualization
    results_json_path = run_output_dir / "results.json"
    TypeAdapter = pydantic.TypeAdapter(List[BenchmarkRunResult])
    with open(results_json_path, "w", encoding="utf-8") as f:
        f.write(TypeAdapter.dump_json(benchmark_run_results, indent=2).decode("utf-8"))
    logger.log_message(f"Raw benchmark results saved to: {results_json_path}")

    logger.finalize_run()

    # Run Log Analysis
    try:
        await analyze_run_logs(run_output_dir)
    except Exception as e:
        logger.log_message(f"Log analysis failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
