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

"""Base class for LLM-based answer generators with shared prompt logic."""

from pathlib import Path

from benchmarks.answer_generators.base import AnswerGenerator
from benchmarks.data_models import AnswerTemplate
from benchmarks.data_models import ApiUnderstandingBenchmarkCase
from benchmarks.data_models import FixErrorBenchmarkCase
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.validation_utils import load_snippet
from benchmarks.validation_utils import TEMPLATES


class LlmAnswerGenerator(AnswerGenerator):
  """
  Abstract base class for answer generators that use an LLM.
  Provides shared logic for prompt construction and context management.
  """

  def __init__(self, context: str | Path | None = None):
    super().__init__()
    self.context = context
    self._prompts_dir = Path(__file__).resolve().parents[0] / "prompts"

  def _read_prompt_template(self, filename: str) -> str:
    """Reads a prompt template from the prompts directory."""
    path = self._prompts_dir / filename
    if not path.exists():
      raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")

  def _get_context_content(self) -> str:
    """Retrieves the context content, reading from file if necessary."""
    if not self.context:
      return ""
    if isinstance(self.context, Path):
      if not self.context.exists():
        raise FileNotFoundError(f"Context file not found: {self.context}")
      with open(self.context, "r", encoding="utf-8") as f:
        return f.read()
    return self.context

  def _create_prompt_for_fix_error(self, case: FixErrorBenchmarkCase) -> str:
    """Creates a prompt for a fix_error benchmark case."""
    requirements_str = ""
    if case.requirements:
      requirements_str = (
          "The generated code must satisfy the following requirements:\n"
      )
      for req in case.requirements:
        requirements_str += f"- {req}\n"
      requirements_str += "\n"

    if not case.unfixed_file:
      raise ValueError("unfixed_file not specified in benchmark case.")

    if not case.unfixed_file.exists():
      raise FileNotFoundError(f"Unfixed file not found: {case.unfixed_file}")

    full_unfixed_content = case.unfixed_file.read_text(encoding="utf-8")

    error_output_section = ""
    if case.error_output:
      error_output_section = (
          "The code currently produces the following"
          f" error:\n```\n{case.error_output}\n```\n\n"
      )

    template = self._read_prompt_template("fix_error_prompt.txt")
    return template.format(
        description=case.description,
        requirements_section=requirements_str,
        error_output_section=error_output_section,
        file_content=full_unfixed_content,
    )

  def _create_prompt_for_multiple_choice(
      self, case: MultipleChoiceBenchmarkCase
  ) -> str:
    """Creates a prompt for a multiple choice benchmark case."""
    options_str = "\n".join(
        f"{key}: {value}" for key, value in case.options.items()
    )

    context_section = ""
    context_content = self._get_context_content()
    if context_content:
      context_section = f"Context:\n{context_content}\n\n"

    code_snippet_section = ""
    if case.code_snippet_ref:
      try:
        code_content = load_snippet(case.code_snippet_ref)
        code_snippet_section = f"Code:\n```python\n{code_content}\n```\n\n"
      except Exception:
        # Warning: Failed to load code snippet. The model will not have this context.
        pass

    template = self._read_prompt_template("multiple_choice_prompt.txt")
    return template.format(
        context_section=context_section,
        code_snippet_section=code_snippet_section,
        question=case.question,
        options=options_str,
    )

  def _create_prompt_for_api_understanding(
      self, case: ApiUnderstandingBenchmarkCase
  ) -> str:
    """Creates a prompt for an api_understanding benchmark case."""
    template_info = TEMPLATES[case.template]
    examples = "\n".join(f"- {example}" for example in template_info.examples)

    context_section = ""
    context_content = self._get_context_content()
    if context_content:
      context_section = f"Context:\n{context_content}\n\n"

    template = self._read_prompt_template("api_understanding_prompt.txt")

    # We must format the template with our values.
    # Note: The JSON examples in the template file should have {{ and }} for literal braces
    # if we are using format(). I did that in the previous step.

    return template.format(
        context_section=context_section,
        class_definition_desc=TEMPLATES[
            AnswerTemplate.CLASS_DEFINITION
        ].description,
        method_definition_desc=TEMPLATES[
            AnswerTemplate.METHOD_DEFINITION
        ].description,
        parameter_definition_desc=TEMPLATES[
            AnswerTemplate.PARAMETER_DEFINITION
        ].description,
        question=case.question,
        template_desc=template_info.description,
        examples=examples,
    )
