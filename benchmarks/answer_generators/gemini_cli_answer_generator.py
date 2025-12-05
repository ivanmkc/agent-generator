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

"""An AnswerGenerator that uses the gemini CLI to generate answers."""

import asyncio
import json
from pathlib import Path
import re
from typing import Any

from benchmarks.answer_generators.gemini_answer_generator import GeminiAnswerGenerator
from benchmarks.answer_generators.llm_base import LlmAnswerGenerator
from benchmarks.data_models import ApiUnderstandingAnswerOutput
from benchmarks.data_models import ApiUnderstandingBenchmarkCase
from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.data_models import FixErrorAnswerOutput
from benchmarks.data_models import FixErrorBenchmarkCase
from benchmarks.data_models import GeneratedAnswer
from benchmarks.data_models import MultipleChoiceAnswerOutput
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.data_models import TraceLogEvent
from benchmarks.data_models import UsageMetadata
from benchmarks.utils import parse_cli_stream_json_output


class GeminiCliAnswerGenerator(GeminiAnswerGenerator):
  """An AnswerGenerator that uses the gemini CLI programmatically."""

  def __init__(  # pylint: disable=super-init-not-called
      self,
      model_name: str = "gemini-2.5-pro",
      context: str | Path | None = None,
      cli_path: str = "gemini",
  ):
    # Initialize the grandparent LlmAnswerGenerator to set up prompts logic
    LlmAnswerGenerator.__init__(self, context=context)

    # Do not call GeminiAnswerGenerator.__init__ to avoid initializing the genai client.
    self.model_name = model_name
    self.context = context
    self.cli_path = cli_path

  @property
  def name(self) -> str:
    """Returns a unique name for this generator instance."""
    # Reuse parent naming logic but indicate CLI usage
    base = super().name
    return base.replace("GeminiAnswerGenerator", "GeminiCliAnswerGenerator")

  async def generate_answer(
      self, benchmark_case: BaseBenchmarkCase
  ) -> GeneratedAnswer:
    """Generates an answer using the gemini CLI."""
    if isinstance(benchmark_case, FixErrorBenchmarkCase):
      prompt = self._create_prompt_for_fix_error(benchmark_case)
      response_schema = FixErrorAnswerOutput
    elif isinstance(benchmark_case, ApiUnderstandingBenchmarkCase):
      prompt = self._create_prompt_for_api_understanding(benchmark_case)
      response_schema = ApiUnderstandingAnswerOutput
    elif isinstance(benchmark_case, MultipleChoiceBenchmarkCase):
      prompt = self._create_prompt_for_multiple_choice(benchmark_case)
      response_schema = MultipleChoiceAnswerOutput
    else:
      raise TypeError(
          f"Unsupported benchmark case type: {type(benchmark_case)}"
      )

    # Append explicit JSON enforcement instructions since CLI doesn't support response_schema
    schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
    prompt += (
        "\n\nIMPORTANT: You must output PURE JSON matching this schema. Do not"
        " include any markdown formatting, explanations, or code blocks"
        f" outside the JSON object.\nJSON Schema:\n{schema_json}\n"
    )

    # Run the CLI command
    cli_response, logs = await self._run_cli_command(prompt)

    # Extract the 'response' field which contains the model's text output
    model_text = cli_response.get("response", "")

    # The model's text output is expected to be a JSON string (because the prompt asks for it)
    # potentially wrapped in markdown code blocks.
    # We must clean it before validation.
    json_content = self._extract_json_from_text(model_text)

    try:
      # Parse the inner JSON content into the Pydantic model
      output = response_schema.model_validate_json(json_content)
    except Exception as e:
      # If parsing fails, wrap it in a generic error or re-raise
      # For now, we'll try to fail gracefully if possible, or just raise
      raise ValueError(
          f"Failed to parse structured output from CLI response: {e}\nOutput"
          f" was: {model_text}\nLogs:\n{logs}"
      ) from e

    usage_metadata = None
    if "stats" in cli_response:
      stats = cli_response["stats"]
      usage_metadata = UsageMetadata(
          total_tokens=stats.get("total_token_count"),
          prompt_tokens=stats.get("prompt_token_count"),
          completion_tokens=stats.get("candidates_token_count"),
      )

    return GeneratedAnswer(
        output=output, trace_logs=logs, usage_metadata=usage_metadata
    )

  async def _run_cli_command(
      self, prompt: str
  ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
    """Executes the gemini CLI command and returns the parsed JSON output and raw logs."""
    args = [
        self.cli_path,
        prompt,  # Pass prompt as positional argument
        "--output-format",
        "stream-json", # Changed from "json" to "stream-json"
        "--model",
        self.model_name,
        "--yolo",
        "--sandbox",
    ]

    # Create subprocess
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    stdout_str = stdout.decode()
    stderr_str = stderr.decode()

    # Parse stdout using the new utility function
    response_dict, logs = parse_cli_stream_json_output(stdout_str)

    if stderr_str:
      logs.append(TraceLogEvent(type="CLI_STDERR", content=stderr_str))

    if proc.returncode != 0:
      error_msg = stderr_str.strip() or stdout_str.strip()
      raise RuntimeError(
          f"Gemini CLI failed with code {proc.returncode}: {error_msg}"
      )

    return response_dict, logs

  def _extract_json_from_text(self, text: str) -> str:
    """Extracts JSON content from a string, handling markdown code blocks."""
    text = text.strip()

    # Match ```json ... ``` or just ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.DOTALL)
    if match:
      return match.group(1)

    # If no code blocks, assume the whole text is JSON
    return text

    
