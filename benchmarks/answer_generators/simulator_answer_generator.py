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

"""Answer generator that runs a CLI simulation."""

import sys
import asyncio
from functools import partial
from pathlib import Path
from typing import Optional


from benchmarks.answer_generators.base import AnswerGenerator
from benchmarks.data_models import BaseBenchmarkCase, SimulatorAnswerOutput
from benchmarks.data_models import GeneratedAnswer
from benchmarks.data_models import SimulatorBenchmarkCase
from benchmarks.logger import BenchmarkLogger
from core.api_key_manager import ApiKeyManager

# HACK: Add tools/simulator to the path so we can import from it
# This is a temporary solution until the simulator is a proper package
project_root = Path(__file__).parent.parent.parent
simulator_path = project_root / "tools"
sys.path.insert(0, str(simulator_path))

from simulator import runner as simulator_runner


class SimulatorAnswerGenerator(AnswerGenerator):
    """Answer generator that runs a CLI simulation."""

    def __init__(
        self,
        backend: str = "gemini-cli",
        logger: Optional[BenchmarkLogger] = None,
        api_key_manager: Optional[ApiKeyManager] = None,
    ):
        super().__init__(logger)
        self.backend = backend
        self.api_key_manager = api_key_manager

    @property
    def name(self) -> str:
        return f"simulator-{self.backend}"

    async def generate_answer(
        self, benchmark_case: BaseBenchmarkCase, run_id: str
    ) -> GeneratedAnswer:
        if not isinstance(benchmark_case, SimulatorBenchmarkCase):
            raise ValueError(
                f"Expected a SimulatorBenchmarkCase, got {type(benchmark_case)}"
            )

        loop = asyncio.get_running_loop()
        runner_func = partial(
            simulator_runner.SimulationRunner.run,
            backend=self.backend,
            api_key_manager=self.api_key_manager,
        )
        result = await loop.run_in_executor(
            None,
            runner_func,
            benchmark_case.simulation_case,
        )

        answer_output = SimulatorAnswerOutput(
            benchmark_type="simulator",
            is_correct=result.success,
            transcript=result.transcript,
            rationale="The simulation completed.",
        )

        return GeneratedAnswer(
            output=answer_output,
        )
