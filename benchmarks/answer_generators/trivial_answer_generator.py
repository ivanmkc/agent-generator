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

"""An answer generator that returns a trivial (empty) answer."""

from benchmarks.answer_generators.base import AnswerGenerator
from benchmarks.data_models import ApiUnderstandingAnswerOutput
from benchmarks.data_models import ApiUnderstandingBenchmarkCase
from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.data_models import FixErrorAnswerOutput
from benchmarks.data_models import FixErrorBenchmarkCase
from benchmarks.data_models import GeneratedAnswer
from benchmarks.data_models import MultipleChoiceAnswerOutput
from benchmarks.data_models import MultipleChoiceBenchmarkCase


class TrivialAnswerGenerator(AnswerGenerator):
  """An answer generator that returns a trivial (empty) answer."""

  @property
  def name(self) -> str:
    """Returns the name of the generator."""
    return "TrivialAnswerGenerator"

  async def generate_answer(
      self, benchmark_case: BaseBenchmarkCase
  ) -> GeneratedAnswer:
    """Returns an empty answer for any benchmark case."""
    if isinstance(benchmark_case, ApiUnderstandingBenchmarkCase):
      output = ApiUnderstandingAnswerOutput(
          code="class Trivial:",
          fully_qualified_class_name="trivial.module",
          rationale="Trivial answer.",
      )
      return GeneratedAnswer(output=output)
    elif isinstance(benchmark_case, FixErrorBenchmarkCase):
      output = FixErrorAnswerOutput(code="", rationale="Trivial answer.")
      return GeneratedAnswer(output=output)
    elif isinstance(benchmark_case, MultipleChoiceBenchmarkCase):
      import random  # pylint: disable=import-outside-toplevel

      options = benchmark_case.options
      if options:
        random_answer_key = random.choice(list(options.keys()))
        output = MultipleChoiceAnswerOutput(
            answer=random_answer_key, rationale="Trivial answer."
        )
      else:
        # Fallback if no options (shouldn't happen with validation)
        output = MultipleChoiceAnswerOutput(
            answer="A", rationale="Trivial answer."
        )
      return GeneratedAnswer(output=output)
    else:
      raise TypeError(f"Unknown benchmark case type: {type(benchmark_case)}")
