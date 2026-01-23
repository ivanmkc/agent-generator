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
)
from benchmarks.answer_generators.base import AnswerGenerator
from benchmarks.config import PODMAN_CONFIG
from benchmarks.data_models import BenchmarkRunResult
from benchmarks.logger import (
    YamlTraceLogger, 
    ConsoleBenchmarkLogger, 
    CompositeLogger
)
import benchmarks.analysis as analysis
from tools.cli.generate_benchmark_report import analyze_run_logs

# Set pandas display options (needed for analysis functions)
pd.set_option("display.max_colwidth", None)
pd.set_option("display.max_rows", None)


def save_static_metadata(
    output_dir: Path,
    generators: List[AnswerGenerator],
    suites_paths: List[str]
) -> None:
    """Saves static metadata about generators and suites to a JSON file and a Markdown file."""
    
    # Extract Generator Metadata (for JSON)
    gen_meta_list = []
    for g in generators:
        model_name = getattr(g, "model_name", "Unknown")
        desc = getattr(g, "description", "No description provided.")
        image_name = getattr(g, "image_name", None)
        
        gen_meta_list.append({
            "name": g.name,
            "model_name": model_name,
            "description": desc,
            "image_name": image_name
        })

    # Extract Suite Metadata
    suite_meta_list = []
    for s_path in suites_paths:
        path_obj = Path(s_path)
        name = path_obj.parent.name
        
        suite_meta_list.append({
            "name": name,
            "path": s_path
        })

    metadata = {
        "timestamp": datetime.now().isoformat(),
        "generators": gen_meta_list,
        "suites": suite_meta_list
    }
    
    # Save JSON
    output_path = output_dir / "run_metadata.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"Failed to save run metadata: {e}")

    # Copy Markdown Cache
    md_output_path = output_dir / "generator_internals.md"
    cached_md_path = Path("notebooks/report/generator_internals.md")
    
    if cached_md_path.exists():
        try:
            import shutil
            shutil.copy(cached_md_path, md_output_path)
            # print(f"Copied generator internals from {cached_md_path}")
        except Exception as e:
            print(f"Failed to copy generator internals markdown: {e}")
    else:
        # Fallback: Generate on the fly if cache is missing
        print("Warning: benchmarks/generator_internals.md not found. Generating on the fly.")
        gen_md_content = ["# Generator Internals (Generated on the fly)\n"]
        for g in generators:
            model_name = getattr(g, "model_name", "Unknown")
            desc = getattr(g, "description", "No description provided.")
            gen_md_content.append(f"### {g.name}")
            gen_md_content.append(f"- **Model:** `{model_name}`")
            gen_md_content.append(f"\n{desc}\n")
            
        try:
            with open(md_output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(gen_md_content))
        except Exception as e:
            print(f"Failed to save generator internals markdown: {e}")


async def run_comparison(
    logger: CompositeLogger, 
    run_output_dir: Path,
    selected_suite: Optional[str] = None,
    selected_generator_filter: Optional[str] = None,
    selected_model_filter: Optional[str] = None,
    retry_on_validation_error: bool = False
) -> List[BenchmarkRunResult]:
    """Sets up and runs the benchmark comparison sequentially per generator."""
    logger.log_message("Configuring benchmark run...")

    debug_suite = "benchmarks/benchmark_definitions/debug_suite/benchmark.yaml"
    debug_single = "benchmarks/benchmark_definitions/debug_single/benchmark.yaml"
    
    standard_suites = [
        "benchmarks/benchmark_definitions/api_understanding/benchmark.yaml",
        "benchmarks/benchmark_definitions/fix_errors/benchmark.yaml",
        "benchmarks/benchmark_definitions/diagnose_setup_errors_mc/benchmark.yaml",
        "benchmarks/benchmark_definitions/configure_adk_features_mc/benchmark.yaml",
        "benchmarks/benchmark_definitions/predict_runtime_behavior_mc/benchmark.yaml",
        debug_single,
    ]

    # Helper for multi-value filtering
    def matches_filter(target: str, filter_str: Optional[str]) -> bool:
        if not filter_str:
            return True
        filters = [f.strip() for f in filter_str.split(",") if f.strip()]
        return any(f in target for f in filters)

    if selected_suite == "debug":
        benchmark_suites = [debug_suite]
    else:
        # Default: Run all standard suites (exclude debug)
        all_suites = standard_suites + [debug_suite]
        # Apply filter if present
        if selected_suite:
             benchmark_suites = [s for s in all_suites if matches_filter(s, selected_suite)]
             if not benchmark_suites:
                raise ValueError(f"Specified suite filter '{selected_suite}' matched no suites.")
        else:
             benchmark_suites = standard_suites

    # Filter generators
    answer_generators: list[AnswerGenerator] = []
    
    # Start with all candidates
    all_candidates = CANDIDATE_GENERATORS
    
    for g in all_candidates:
        # Check Generator Name Filter
        if not matches_filter(g.name, selected_generator_filter):
            continue
            
        # Check Model Name Filter
        g_model = getattr(g, "model_name", "Unknown")
        # Handle enum or string
        if hasattr(g_model, "value"): 
            g_model = g_model.value
        
        if not matches_filter(str(g_model), selected_model_filter):
            continue
            
        answer_generators.append(g)

    if not answer_generators:
         logger.log_message(f"Warning: No generators matched the provided filters (gen: {selected_generator_filter}, model: {selected_model_filter}).")

    # Save Static Metadata
    save_static_metadata(run_output_dir, answer_generators, benchmark_suites)

    logger.log_message(f"Executing benchmarks with {len(answer_generators)} generators on {len(benchmark_suites)} suites...")

    all_results = []

    for generator in answer_generators:
        # Use logger section for the generator block
        with logger.section(f"Generator: {generator.name}"):
            
            # Filter suites based on generator compatibility
            current_suites = list(benchmark_suites)
            # # TODO: Remove this filter when StructuredWorkflowAdk can adapt its output schema
            # # to match different benchmark types (e.g., ApiUnderstanding). Currently, its FinalResponse
            # # is hardcoded to FixErrorAnswerOutput.
            # if "StructuredWorkflowAdk" in generator.name or "BaselineWorkflowAdk" in generator.name:
            #      current_suites = [s for s in current_suites if "fix_errors" in s or "debug_suite" in s]
            #      if not current_suites:
            #          logger.log_message(f"Skipping: No compatible suites found (requires 'fix_errors').")
            #          continue
            #      logger.log_message(f"Restricted suites to: {current_suites}")

            try:
                logger.log_message(f"Running benchmarks on suites: {current_suites}")
                logger.log_message(f"Setting up...")
                await generator.setup()

                # Determine if we should use a proxy for the actual execution
                target_generator = generator

                # # For Podman generators, create a lightweight proxy that points to the running container
                # if isinstance(generator, GeminiCliPodmanAnswerGenerator):
                #     if hasattr(generator, "_base_url") and generator._base_url:
                #         logger.log_message(
                #             f"Creating proxy for execution at {generator._base_url}"
                #         )
                #         target_generator = GeminiCliPodmanAnswerGenerator(
                #             dockerfile_dir=generator.dockerfile_dir,
                #             image_name=generator.image_name,
                #             image_definitions=generator._image_definitions,
                #             model_name=generator.model_name,
                #             context_instruction=generator.context_instruction,
                #             service_url=generator._base_url,
                #         )

                # Adjust concurrency for heavy generators
                concurrency = PODMAN_CONFIG.MAX_GLOBAL_CONCURRENCY

                # Note: run_benchmarks handles its own section logging for the execution
                results = await benchmark_orchestrator.run_benchmarks(
                    benchmark_suites=current_suites,
                    answer_generators=[target_generator],
                    max_concurrency=concurrency,
                    max_retries=3,
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
    json_logger = YamlTraceLogger(output_dir=str(run_output_dir), filename="trace.yaml")
    console_logger = ConsoleBenchmarkLogger()
    logger = CompositeLogger([console_logger, json_logger])

    # Execute the benchmarks
    benchmark_run_results = await run_comparison(
        logger=logger, 
        run_output_dir=run_output_dir,
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
        await analyze_run_logs(run_output_dir, model_name="gemini-3-pro-preview")
    except Exception as e:
        logger.log_message(f"Log analysis failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
