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

"""Abstract base class for answer generators."""

import abc
from typing import Optional

from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.data_models import GeneratedAnswer
from benchmarks.logger import BenchmarkLogger


class AnswerGenerator(abc.ABC):
    """Abstract base class for answer generators."""

    def __init__(self, logger: Optional[BenchmarkLogger] = None):
        self.logger = logger

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Returns a unique name for this generator instance, reflecting its configuration."""
        pass

    @abc.abstractmethod
    async def generate_answer(
        self, benchmark_case: BaseBenchmarkCase, run_id: str
    ) -> GeneratedAnswer:
        """
        Generates an answer for the given benchmark case.

        Args:
            benchmark_case: The benchmark case to solve.
            run_id: A unique identifier for this execution run (used for sticky resources).

        Returns:
            A GeneratedAnswer object containing the structured output and metadata.
        """
        raise NotImplementedError

    async def get_mcp_tools(self) -> list[str]:
        """Returns a list of available MCP tools."""
        return []

    async def setup(self) -> None:
        """
        Performs any necessary setup (e.g., deploying services) before running benchmarks.

        This method MUST be idempotent. Calling it multiple times should not cause issues
        and should simply ensure the generator is in a ready state.
        """
        pass

    async def teardown(self) -> None:
        """Performs cleanup (e.g., stopping containers)."""
        pass
