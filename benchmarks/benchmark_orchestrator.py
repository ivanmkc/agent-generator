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
from pathlib import Path
import time
from typing import List
from typing import Optional

import tenacity

import yaml

from benchmarks.answer_generators import AnswerGenerator
from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.data_models import BenchmarkFile
from benchmarks.data_models import BenchmarkResultType
from benchmarks.data_models import BenchmarkRunResult
from benchmarks.data_models import ApiUnderstandingBenchmarkCase, MultipleChoiceBenchmarkCase, FixErrorBenchmarkCase
from benchmarks.logger import BenchmarkLogger


async def _run_single_benchmark(
    suite_file: str,
    case: BaseBenchmarkCase,
    generator: AnswerGenerator,
    semaphore: asyncio.Semaphore,
    logger: BenchmarkLogger,
    max_retries: int,
    min_wait: float,
    max_wait: float,
) -> BenchmarkRunResult:
  """Helper coroutine to run one benchmark case and return its result."""
  async with semaphore:
    runner = case.runner

    generated_answer = None
    ground_truth = None

    # TODO: Refactor so BaseBenchmarkCase implementations are no longer dependencies but rather only BaseBenchmarkCase is imported.
    if isinstance(case, FixErrorBenchmarkCase) and case.fixed_file:
      if case.fixed_file.exists():
        ground_truth = case.fixed_file.read_text(encoding="utf-8")
    elif isinstance(case, MultipleChoiceBenchmarkCase):
      ground_truth = case.correct_answer
    elif isinstance(case, ApiUnderstandingBenchmarkCase):
      # For now, just take the first valid answer as the ground truth example
      if case.answers:
        ground_truth = case.answers[0].answer

    start_time = time.time()
    try:
      retryer = tenacity.AsyncRetrying(
          stop=tenacity.stop_after_attempt(max_retries),
          wait=tenacity.wait_exponential(
              multiplier=1, min=min_wait, max=max_wait
          ),
          retry=tenacity.retry_if_exception_type(Exception),
          reraise=True,
      )

      async for attempt in retryer:
        with attempt:
          generated_answer = await generator.generate_answer(case)

    except Exception as e:
      error_message = f"Generation failed after {max_retries} retries: {e}"
      if logger:
        logger.log_generation_failure(
            benchmark_name=case.get_identifier(),
            error_message=error_message,
            prompt="",
        )

      from benchmarks.data_models import BenchmarkErrorType

      # Try to map common generation errors
      gen_error_type = BenchmarkErrorType.OTHER_ERROR
      exc_name = type(e).__name__
      # Simple mapping attempt
      for member in BenchmarkErrorType:
        if member.value == exc_name:
          gen_error_type = member
          break

      return BenchmarkRunResult(
          suite=str(Path(suite_file).absolute()),
          benchmark_name=case.get_identifier(),
          benchmark_type=case.benchmark_type,
          answer_generator=generator.name,
          status=BenchmarkResultType.FAIL_CRASH,
          result=0,
          answer="",
          validation_error=error_message,
          error_type=gen_error_type,
          temp_test_file=None,
          latency=time.time() - start_time,
          ground_truth=ground_truth,
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
          trace_logs=(
              generated_answer.trace_logs if generated_answer else None
          ),
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
      usage_metadata=generated_answer.usage_metadata
      if generated_answer
      else None,
      ground_truth=ground_truth,
  )


async def run_benchmarks(
    benchmark_suites: List[str],
    answer_generators: List[AnswerGenerator],
    max_concurrency: int = 50,
    max_retries: int = 2,
    min_wait: float = 4.0,
    max_wait: float = 20.0,
    logger: Optional[BenchmarkLogger] = None,
) -> List[BenchmarkRunResult]:
  """
  Runs all benchmark suites against all answer generators in parallel and returns raw results.
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
  tasks = []
  results = []
  completed_tasks_count = 0

  # Ensure all generators are set up and their names are finalized before use.
  for generator in answer_generators:
      print(f"  - Setting up answer generator: {generator.name}...")
      await generator.setup()  # Initialize/Deploy if needed

  # Initialize tracking dictionaries after setup, when generator names are stable.
  tasks_by_generator = {g.name: 0 for g in answer_generators}
  completed_by_generator = {g.name: 0 for g in answer_generators}

  for suite_file in benchmark_suites:
    print(f"--- Loading benchmark suite: {suite_file} ---")
    with open(suite_file, "r", encoding="utf-8") as f:
      data = yaml.safe_load(f)
    benchmark_file = BenchmarkFile.model_validate(data)

    for generator in answer_generators:
      print(
          f"  - Adding benchmarks for answer generator: {generator.name}..."
      )
      for case in benchmark_file.benchmarks:
        tasks.append(
            _run_single_benchmark(
                suite_file,
                case,
                generator,
                semaphore,
                logger,
                max_retries,
                min_wait,
                max_wait,
            )
        )
        tasks_by_generator[generator.name] += 1

  print(
      f"\n--- Running {len(tasks)} benchmarks in parallel"
      f" (max_concurrency={max_concurrency}) ---\n"
  )

  for task_future in asyncio.as_completed(tasks):
    result = await task_future
    results.append(result)
    completed_by_generator[result.answer_generator] += 1
    completed_tasks_count += 1

  # Final progress reporting for each generator
  print("\n--- Summary of Progress per Answer Generator ---")
  for gen_name, total_tasks in tasks_by_generator.items():
    completed = completed_by_generator[gen_name]
    print(f"  - {gen_name}: {completed} of {total_tasks} tasks completed.")

  if logger:
    logger.finalize_run()
  return results
