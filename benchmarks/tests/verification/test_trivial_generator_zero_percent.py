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

"""Verification test to ensure TrivialAnswerGenerator yields 0% pass rate on non-MC benchmarks."""

import pytest

from benchmarks import benchmark_orchestrator
from benchmarks.answer_generators import TrivialAnswerGenerator
from benchmarks.logger import YamlTraceLogger


@pytest.mark.asyncio
async def test_trivial_generator_is_zero_percent_on_non_mc():
    """
    Runs TrivialAnswerGenerator against non-MC benchmark suites (fix_errors, api_understanding).
    Asserts that NO tests pass. A trivial/empty answer should never satisfy the requirements
    of these complex tasks.
    """
    logger = YamlTraceLogger(output_dir="traces_verification")

    # Define non-MC suites
    benchmark_suites = [
        "benchmarks/benchmark_definitions/fix_errors/benchmark.yaml",
        "benchmarks/benchmark_definitions/api_understanding/benchmark.yaml",
    ]

    # Run benchmarks
    results = await benchmark_orchestrator.run_benchmarks(
        benchmark_suites=benchmark_suites,
        answer_generators=[TrivialAnswerGenerator()],
        max_concurrency=20,
        logger=logger,
    )

    # Filter for TrivialAnswerGenerator (though it's the only one used)
    trivial_results = [
        r for r in results if r.answer_generator == "TrivialAnswerGenerator"
    ]

    # Count passes
    passed_count = sum(1 for r in trivial_results if r.result == 1)
    passed_details = [
        f"{r.benchmark_name} (Suite: {r.suite})"
        for r in trivial_results
        if r.result == 1
    ]

    assert passed_count == 0, (
        f"TrivialAnswerGenerator passed {passed_count} benchmarks! This indicates"
        f" loose validation.\nPassed cases: {passed_details}"
    )
