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

"""An answer generator that returns the ground truth answer."""

from pathlib import Path
import re
import textwrap

from benchmarks.answer_generators.base import AnswerGenerator
from benchmarks.data_models import ApiUnderstandingAnswerOutput
from benchmarks.data_models import ApiUnderstandingBenchmarkCase
from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.data_models import FixErrorAnswerOutput
from benchmarks.data_models import FixErrorBenchmarkCase
from benchmarks.data_models import GeneratedAnswer
from benchmarks.data_models import MultipleChoiceAnswerOutput
from benchmarks.data_models import MultipleChoiceBenchmarkCase


class GroundTruthAnswerGenerator(AnswerGenerator):
    """An answer generator that returns the ground truth answer."""

    @property
    def name(self) -> str:
        """Returns the name of the generator."""
        return "GroundTruthAnswerGenerator"

    async def generate_answer(
        self, benchmark_case: BaseBenchmarkCase
    ) -> GeneratedAnswer:
        """Returns the ground truth answer for the benchmark case."""
        if isinstance(benchmark_case, FixErrorBenchmarkCase):
            # Extract the answer code from the fixed_file.
            file_path = benchmark_case.fixed_file

            if not file_path:
                raise ValueError("fixed_file not specified in benchmark case.")

            if not file_path.exists():
                raise FileNotFoundError(f"Fixed file not found: {file_path}")

            code = file_path.read_text()
            code = code.strip()

            rationale = "Ground truth answer extracted from fixed file."
            output = FixErrorAnswerOutput(code=code, rationale=rationale)
            return GeneratedAnswer(output=output)
        elif isinstance(benchmark_case, ApiUnderstandingBenchmarkCase):
            answer = benchmark_case.answers[0]
            output = ApiUnderstandingAnswerOutput(
                code=answer.answer,
                fully_qualified_class_name=answer.fully_qualified_class_name[0],
                rationale="Ground truth answer.",
            )
            return GeneratedAnswer(output=output)
        elif isinstance(benchmark_case, MultipleChoiceBenchmarkCase):
            output = MultipleChoiceAnswerOutput(
                answer=benchmark_case.correct_answer, rationale="Ground truth answer."
            )
            return GeneratedAnswer(output=output)
        else:
            raise TypeError(f"Unknown benchmark case type: {type(benchmark_case)}")
