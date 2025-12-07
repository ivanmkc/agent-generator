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
from typing import Any, Optional

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
from pydantic import BaseModel


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
      self,
      benchmark_case: BaseBenchmarkCase
  ) -> GeneratedAnswer:
    """Generates an answer using the gemini CLI."""
    prompt: str
    response_schema: BaseModel | None = None

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

    # Append explicit JSON enforcement instructions to the prompt.
    # This guides the model to produce structured output.
    schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
    prompt += (
        "\n\nIMPORTANT: You must output PURE JSON matching this schema. Do not"
        " include any markdown formatting, explanations, or code blocks"
        f" outside the JSON object.\nJSON Schema:\n{schema_json}\n"
    )

    # Construct cli_args to always include --output-format stream-json, --model, --yolo, --debug, and the prompt as a positional argument
    cli_args = [
        "--output-format",
        "stream-json",
        "--model",
        self.model_name,
        "--yolo",
        "--debug",
        prompt, # Positional argument for the prompt
        # "--sandbox", # Removed because we are already in a container
    ]

    # Run the CLI command
    cli_response_dict, logs = await self._run_cli_command(cli_args)

    # Extract the 'response' field which contains the model's text output
    model_text = cli_response_dict.get("response", "")

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
    if "stats" in cli_response_dict:
      stats = cli_response_dict["stats"]
      usage_metadata = UsageMetadata(
          total_tokens=stats.get("total_token_count"),
          prompt_tokens=stats.get("prompt_token_count"),
          completion_tokens=stats.get("candidates_token_count"),
      )

    return GeneratedAnswer(
        output=output, trace_logs=logs, usage_metadata=usage_metadata
    )

  async def _run_cli_command(
      self,
      cli_args: list[str],
      direct_command_parts: Optional[list[str]] = None
  ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
    """Executes the gemini CLI command and returns the parsed JSON output and raw logs."""
    args = [
        self.cli_path,
    ]
    if direct_command_parts:
        args.extend(direct_command_parts)
    else:
        args.extend(cli_args)

    # Create subprocess
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    stdout_str = stdout.decode()
    stderr_str = stderr.decode()

    # Initialize logs with stderr content first
    logs: list[TraceLogEvent] = []
    for line in stderr_str.splitlines():
        if line.strip():
            logs.append(TraceLogEvent(type="CLI_STDERR", source="podman", content=line.strip()))

    # Parse stdout. If stream-json, parse events. Otherwise, treat as raw message.
    response_dict = {"stdout": stdout_str, "stderr": stderr_str, "exit_code": proc.returncode, "response": ""}
    if "--output-format" in cli_args and "stream-json" in cli_args:
        parsed_response_dict, parsed_logs = parse_cli_stream_json_output(stdout_str)
        response_dict.update(parsed_response_dict)
        logs.extend(parsed_logs)
    else:
        # If not stream-json, treat stdout as a single response message for logging purposes
        if stdout_str.strip():
            logs.append(TraceLogEvent(type="CLI_STDOUT_RAW", source="podman", content=stdout_str.strip()))
        response_dict["response"] = stdout_str.strip()  # Direct text response

    if proc.returncode != 0:
      error_msg = stderr_str.strip() or stdout_str.strip()
      raise RuntimeError(
          f"Gemini CLI failed with code {proc.returncode}: {error_msg}"
      )

    return response_dict, logs

  async def get_mcp_tools(self) -> list[str]:
    """Returns a list of available MCP tools (servers) and extensions."""
    tools = []

    # 1. List MCP Servers
    # Output format: "✓ context7: https://..." or similar
    try:
        mcp_res, _ = await self._run_cli_command([], direct_command_parts=["mcp", "list"])
        for line in mcp_res.get("stdout", "").splitlines():
            # Look for checkmark or name followed by URL
            # e.g. "✓ context7: ..."
            match = re.search(r"(?:✓|\*|-)?\s*([a-zA-Z0-9_-]+):\s*https?://", line)
            if match:
                tools.append(match.group(1))
    except Exception:
        pass

    # 2. List Extensions
    # Output format: "adk-docs-ext (v...)" or just list
    try:
        ext_res, _ = await self._run_cli_command([], direct_command_parts=["extensions", "list"])
        for line in ext_res.get("stdout", "").splitlines():
             stripped = line.strip()
             # Heuristic to filter out empty lines, errors, headers, or "No extensions" messages
             if (stripped and 
                 not stripped.lower().startswith("error") and 
                 not stripped.lower().startswith("usage") and
                 "no extensions installed" not in stripped.lower()):
                 tools.append(stripped.split()[0]) # Take first word as potential name
    except Exception:
        pass

    return list(set(tools))

  def _extract_json_from_text(self, text: str) -> str:
    """Extracts JSON content from a string, handling markdown code blocks."""
    text = text.strip()

    # Match ```json ... ``` or just ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.DOTALL)
    if match:
      return match.group(1)

    # If no code blocks, assume the whole text is JSON
    return text