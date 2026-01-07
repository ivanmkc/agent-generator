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

"""A test rig to validate the benchmarks against the codebase."""

import asyncio
import contextlib
from pathlib import Path
import time
import random
import traceback
import uuid
import datetime
from typing import List
from typing import Optional

import tenacity
import pydantic

import yaml

from benchmarks.answer_generators import AnswerGenerator
from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.data_models import BenchmarkFile
from benchmarks.data_models import BenchmarkResultType
from benchmarks.data_models import BenchmarkRunResult
from benchmarks.data_models import GenerationAttempt
from benchmarks.data_models import BenchmarkGenerationError
from benchmarks.logger import BenchmarkLogger
import benchmarks.validation_utils as validation_utils

# Default configuration constants
DEFAULT_MAX_CONCURRENCY = 10
DEFAULT_MAX_RETRIES = 2
DEFAULT_MIN_WAIT = 4.0
DEFAULT_MAX_WAIT = 20.0


async def _run_single_benchmark(
    suite_file: str,
    case: BaseBenchmarkCase,
    generator: AnswerGenerator,
    semaphore: asyncio.Semaphore,
    logger: BenchmarkLogger,
    max_retries: int,
    min_wait: float,
    max_wait: float,
    retry_on_validation_error: bool = True,
) -> BenchmarkRunResult:
    """Helper coroutine to run one benchmark case and return its result."""
    async with semaphore:
        runner = case.runner

        generated_answer = None
        ground_truth = case.get_ground_truth()
        attempts_history: List[GenerationAttempt] = []

        start_time = time.time()

        # Manual Retry Loop
        for attempt_idx in range(max_retries + 1):
            attempt_start = time.time()
            # Generate a unique run ID for each attempt
            run_id = f"run_{uuid.uuid4().hex}"
            try:
                # Pass the run_id to the generator
                generated_answer = await generator.generate_answer(case, run_id=run_id)

                # Extract answer string for history
                attempt_answer_str = ""
                if generated_answer and generated_answer.output:
                    if hasattr(generated_answer.output, "code"):
                        attempt_answer_str = generated_answer.output.code
                    elif hasattr(generated_answer.output, "answer"):
                        attempt_answer_str = generated_answer.output.answer
                    else:
                        attempt_answer_str = str(generated_answer.output)

                # Record Success
                attempts_history.append(
                    GenerationAttempt(
                        attempt_number=attempt_idx + 1,
                        status="success",
                        duration=time.time() - attempt_start,
                        api_key_id=generated_answer.api_key_id,
                        trace_logs=generated_answer.trace_logs,
                        answer=attempt_answer_str,
                        rationale=generated_answer.output.rationale if generated_answer.output else None,
                        usage_metadata=generated_answer.usage_metadata,
                    )
                )
                break  # Exit loop on success

            except Exception as e:
                # Record Failure
                # We do NOT print stack traces to console anymore to keep the output clean.
                # The logger will summarize the failure at the end.
                
                # Extract metadata if available in the custom exception
                failed_key_id = None
                failed_logs = None
                failed_usage = None
                original_exception = e
                
                if isinstance(e, BenchmarkGenerationError):
                    failed_key_id = e.api_key_id
                    failed_logs = e.trace_logs
                    failed_usage = e.usage_metadata
                    original_exception = e.original_exception
                
                attempts_history.append(
                    GenerationAttempt(
                        attempt_number=attempt_idx + 1,
                        status="failure",
                        error_message=str(e),
                        duration=time.time() - attempt_start,
                        api_key_id=failed_key_id,
                        trace_logs=failed_logs,
                        usage_metadata=failed_usage,
                    )
                )

                # Check if we should retry
                should_retry = attempt_idx < max_retries
                
                # Check for validation error logic
                is_validation_error = isinstance(original_exception, pydantic.ValidationError)
                if is_validation_error and not retry_on_validation_error:
                    should_retry = False

                if should_retry:
                    # Release the key for this failed run before retrying
                    if generator.api_key_manager and failed_key_id:
                        generator.api_key_manager.release_run(run_id)
                    # Exponential Backoff: min_wait * 2^attempt
                    delay = min(max_wait, min_wait * (2**attempt_idx))
                    # Add jitter (0.5 to 1.5 multiplier)
                    delay *= 0.5 + random.random()
                    await asyncio.sleep(delay)
                else:
                    # Final Failure after all retries (or if retry aborted)
                    error_message = f"Generation failed after {attempt_idx + 1} attempts. Last error: {e}"
                    if logger:
                        # Log the final failure summary
                        # We use log_test_result even for generation failure to get the consistent block format
                        logger.log_test_result(
                            benchmark_name=case.get_identifier(),
                            result=BenchmarkResultType.FAIL_GENERATION,
                            validation_error=error_message,
                            temp_test_file=None,
                            generation_attempts=attempts_history,
                        )

                    from benchmarks.data_models import BenchmarkErrorType

                    # Try to map common generation errors
                    gen_error_type = BenchmarkErrorType.OTHER_ERROR
                    exc_name = type(original_exception).__name__
                    for member in BenchmarkErrorType:
                        if member.value == exc_name:
                            gen_error_type = member
                            break

                    return BenchmarkRunResult(
                        suite=str(Path(suite_file).absolute()),
                        benchmark_name=case.get_identifier(),
                        benchmark_type=case.benchmark_type,
                        answer_generator=generator.name,
                        status=BenchmarkResultType.FAIL_GENERATION,
                        result=0,
                        answer="",
                        validation_error=error_message,
                        error_type=gen_error_type,
                        temp_test_file=None,
                        latency=time.time() - start_time,
                        ground_truth=ground_truth,
                        generation_attempts=attempts_history,
                    )

        latency = time.time() - start_time

        result, validation_error, temp_file_path, error_type = (
            await runner.run_benchmark(case, generated_answer)
        )

        if logger:
            logger.log_test_result(
                benchmark_name=case.get_identifier(),
                result=result,
                validation_error=validation_error,
                temp_test_file=Path(temp_file_path) if temp_file_path else None,
                answer_data=(
                    generated_answer.output.model_dump() if generated_answer else None
                ),
                trace_logs=(generated_answer.trace_logs if generated_answer else None),
                generation_attempts=attempts_history,
            )

        # Extract the actual answer string based on the output type
        answer_str = ""
        if generated_answer and generated_answer.output:
            if hasattr(generated_answer.output, "code"):
                answer_str = generated_answer.output.code
            elif hasattr(generated_answer.output, "answer"):
                answer_str = generated_answer.output.answer
            else:
                answer_str = str(generated_answer.output)

    return BenchmarkRunResult(
        suite=str(Path(suite_file).absolute()),
        benchmark_name=case.get_identifier(),
        benchmark_type=case.benchmark_type,
        answer_generator=generator.name,
        status=result,
        result=1 if result == BenchmarkResultType.PASS else 0,
        answer=answer_str,
        rationale=(
            generated_answer.output.rationale if generated_answer.output else None
        ),
        validation_error=validation_error,
        error_type=error_type,
        temp_test_file=temp_file_path,
        latency=latency,
        trace_logs=generated_answer.trace_logs if generated_answer else None,
        usage_metadata=generated_answer.usage_metadata if generated_answer else None,
        ground_truth=ground_truth,
        generation_attempts=attempts_history,
    )


async def run_benchmarks(
    benchmark_suites: List[str],
    answer_generators: List[AnswerGenerator],
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    max_retries: int = DEFAULT_MAX_RETRIES,
    min_wait: float = DEFAULT_MIN_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
    retry_on_validation_error: bool = True,
    logger: Optional[BenchmarkLogger] = None,
) -> List[BenchmarkRunResult]:
    """
    Runs all benchmark suites against all answer generators.

    Execution is serialized by AnswerGenerator to manage resources (e.g. one Podman image at a time),
    but benchmarks *within* a single generator run in parallel up to `max_concurrency`.
    """
    # Check for duplicate generator names to prevent result collisions
    generator_names = [g.name for g in answer_generators]
    if len(generator_names) != len(set(generator_names)):
        duplicates = {
            name for name in generator_names if generator_names.count(name) > 1
        }
        raise ValueError(
            f"Duplicate answer generator names detected: {duplicates}. "
            "Please ensure all generators have unique names."
        )

    semaphore = asyncio.Semaphore(max_concurrency)
    results = []

    # Initialize tracking dictionaries
    # We'll populate total tasks as we process each generator
    completed_by_generator = {g.name: 0 for g in answer_generators}
    tasks_by_generator = {g.name: 0 for g in answer_generators}

    for generator in answer_generators:
        # Use context manager for section logging if logger is available
        ctx = logger.section(f"Agent: {generator.name}") if logger else contextlib.nullcontext()
        
        with ctx:
            if not logger:
                print(f"\n=== Processing Answer Generator: {generator.name} ===")

            if logger:
                logger.log_message(f"Setting up answer generator: {generator.name}...")
            else:
                print(f"  - Setting up answer generator: {generator.name}...")
            
            await generator.setup()  # Initialize/Deploy if needed

            generator_tasks = []

            for suite_file in benchmark_suites:
                if logger:
                    logger.log_message(f"Loading benchmark suite: {suite_file}")
                else:
                    print(f"  - Loading benchmark suite: {suite_file}")
                    
                with open(suite_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                benchmark_file = BenchmarkFile.model_validate(data)

                for case in benchmark_file.benchmarks:
                    generator_tasks.append(
                        _run_single_benchmark(
                            suite_file,
                            case,
                            generator,
                            semaphore,
                            logger,
                            max_retries,
                            min_wait,
                            max_wait,
                            retry_on_validation_error,
                        )
                    )

            total_gen_tasks = len(generator_tasks)
            tasks_by_generator[generator.name] = total_gen_tasks

            msg = (f"Running {total_gen_tasks} benchmarks in parallel for {generator.name}"
                   f" (max_concurrency={max_concurrency})..."
            )
            if logger:
                logger.log_message(msg)
            else:
                print(f"  - {msg}")

            start_gen_time = time.time()
            last_log_time = time.time()
            log_interval_minutes = 1  # Log every minute

            for task_future in asyncio.as_completed(generator_tasks):
                result = await task_future
                results.append(result)
                completed_by_generator[result.answer_generator] += 1

                current_time = time.time()
                if (current_time - last_log_time) / 60 >= log_interval_minutes:
                    elapsed_minutes = (current_time - start_gen_time) / 60
                    completed_tasks = completed_by_generator[result.answer_generator]
                    total_tasks = tasks_by_generator[result.answer_generator]
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    msg = (f"[{timestamp}] - {generator.name}: {completed_tasks}/{total_tasks} tasks "
                           f"completed in {elapsed_minutes:.1f} minutes.")
                    if logger:
                        logger.log_message(msg)
                    else:
                        print(f"  {msg}")
                    last_log_time = current_time

            if logger:
                logger.log_message(f"Completed all tasks for {generator.name}.")
                logger.log_message(f"Tearing down answer generator: {generator.name}...")
            else:
                print(f"  - Completed all tasks for {generator.name}.")
                print(f"  - Tearing down answer generator: {generator.name}...")
            
            try:
                await generator.teardown()
            except Exception as e:
                msg = f"Warning: Teardown failed for {generator.name}: {e}"
                if logger:
                    logger.log_message(msg)
                else:
                    print(f"  - {msg}")

    # Final progress reporting
    if logger:
        with logger.section("Summary of Progress"):
            for gen_name, total_tasks in tasks_by_generator.items():
                completed = completed_by_generator[gen_name]
                logger.log_message(f"{gen_name}: {completed} of {total_tasks} tasks completed.")
        
        # Log the summary table
        logger.log_summary_table(results)
        
        logger.finalize_run()
    return results
