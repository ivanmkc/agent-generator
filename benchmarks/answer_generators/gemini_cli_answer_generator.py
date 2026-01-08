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
import logging
import json
from pathlib import Path
import re
from typing import Any


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
from benchmarks.data_models import BenchmarkGenerationError
from benchmarks.utils import parse_cli_stream_json_output
from pydantic import BaseModel
from benchmarks.api_key_manager import ApiKeyManager, KeyType
from benchmarks.answer_generators.gemini_answer_generator import GeminiAnswerGenerator


class GeminiCliAnswerGenerator(GeminiAnswerGenerator):
    """An AnswerGenerator that uses the gemini CLI programmatically."""

    def __init__(  # pylint: disable=super-init-not-called
        self,
        model_name: str = "gemini-2.5-pro",
        context: str | Path | None = None,
        cli_path: str = "gemini",
        api_key_manager: ApiKeyManager | None = None,
    ):
        # Call the direct parent (GeminiAnswerGenerator) and pass relevant arguments.
        super().__init__(
            model_name=model_name, context=context, api_key_manager=api_key_manager
        )

        # cli_path is specific to this class and not passed up the chain.
        self.cli_path = cli_path
        self._setup_completed = False

    @property
    def name(self) -> str:
        """Returns a unique name for this generator instance."""
        # Reuse parent naming logic but indicate CLI usage
        base = super().name
        return base.replace("GeminiAnswerGenerator", "GeminiCliAnswerGenerator")

    @property
    def description(self) -> str:
        """Returns a detailed description of the generator."""
        desc = f"**Model:** {self.model_name}\n\n"
        desc += "**Type:** Gemini CLI (Local Process)\n\n"
        
        context_content = self._get_context_content()
        if context_content:
            preview = context_content[:200]
            desc += f"**Context Preview:**\n> {preview}..."
            
        return desc

    async def generate_answer(
        self, benchmark_case: BaseBenchmarkCase, run_id: str
    ) -> GeneratedAnswer:
        """Generates an answer using the gemini CLI."""
        prompt: str
        response_schema: BaseModel | None = None

        if isinstance(benchmark_case, FixErrorBenchmarkCase):
            prompt = self._create_prompt_for_fix_error(benchmark_case)
            response_schema = FixErrorAnswerOutput
        elif isinstance(benchmark_case, ApiUnderstandingBenchmarkCase):
            prompt = self._create_prompt_for_api_understanding(benchmark_case)
            output_schema_class = ApiUnderstandingAnswerOutput
            response_schema = ApiUnderstandingAnswerOutput
        elif isinstance(benchmark_case, MultipleChoiceBenchmarkCase):
            prompt = self._create_prompt_for_multiple_choice(benchmark_case)
            response_schema = MultipleChoiceAnswerOutput
        else:
            raise TypeError(f"Unsupported benchmark case type: {type(benchmark_case)}")

        # Append explicit JSON enforcement instructions to the prompt.
        # This guides the model to produce structured output.
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        prompt += (
            "\n\nIMPORTANT: You must output PURE JSON matching this schema. Do not"
            " include any markdown formatting, explanations, or code blocks"
            f" outside the JSON object.\nJSON Schema:\n{schema_json}\n"
        )

        # Construct cli_args to always include --output-format stream-json, --model, --yolo, --debug, and the prompt as a positional argument
        command_parts = [
            self.cli_path,
            "--output-format",
            "stream-json",
            "--model",
            self.model_name,
            "--yolo",
            "--debug",
            prompt,  # Positional argument for the prompt
        ]
        
        # Resolve API Key for this run
        extra_env = {}
        api_key_id: Optional[str] = None
        if not self.api_key_manager:
            raise RuntimeError("ApiKeyManager is not configured for GeminiCliAnswerGenerator.")

        current_key, api_key_id = self.api_key_manager.get_key_for_run(run_id, KeyType.GEMINI_API)
        if not current_key:
            raise RuntimeError(f"No API key available for run_id '{run_id}' from ApiKeyManager.")
        
        extra_env["GEMINI_API_KEY"] = current_key

        try:
            # Run the CLI command
            cli_response_dict, logs = await self.run_cli_command(command_parts, extra_env=extra_env)

            # Report success
            self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=True)
            # Note: We don't easily detect 429s from CLI text output here unless we parse logs deeply.
            # Assuming CLI handles retries or we catch generic failures.

        except Exception as e:
            # Report Failure 
            self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=False, error_message=str(e))
            raise BenchmarkGenerationError(f"Gemini CLI Generation failed: {e}", original_exception=e, api_key_id=api_key_id) from e
        finally:
            self.api_key_manager.release_run(run_id)

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
            # Report Failure if key was used
            self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=False)

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

        # Use our managed key ID if available, otherwise what CLI returned (if any)
        final_api_key_id = api_key_id or cli_response_dict.get("api_key_id")

        return GeneratedAnswer(
            output=output,
            trace_logs=logs,
            usage_metadata=usage_metadata,
            api_key_id=final_api_key_id,
        )

    async def run_cli_command(
        self,
        command_parts: list[str],
        extra_env: dict[str, str] = None, # Added argument
    ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
        """Executes the gemini CLI command and returns the parsed JSON output and raw logs.

        This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement run_cli_command")

    async def setup(self, force_deploy: bool = False) -> None:
        """Performs any necessary setup (e.g., starting containers)."""
        self._setup_completed = True

    async def get_mcp_tools(self) -> list[str]:
        """Returns a list of available MCP tools (servers)."""
        if not self._setup_completed:
            raise RuntimeError(
                f"Generator {self.name} has not been set up. Please call setup() first."
            )
        tools = []

        try:
            mcp_res, _ = await self.run_cli_command([self.cli_path, "mcp", "list"])
            for line in mcp_res.get("stdout", "").splitlines():
                # 1. Clean the line of ANSI codes immediately
                clean_line = self._strip_ansi(line).strip()

                if (
                    not clean_line
                    or clean_line == "Configured MCP servers:"
                    or clean_line == "(none)"
                ):
                    continue

                # 2. Extract part before the first colon
                # TS Output: "${statusIndicator} ${serverName} (from ...): ..."
                # Example: "✓ weather (from ext): ..."
                tool_name_with_status = clean_line.split(":", 1)[0].strip()

                # 3. Remove leading status indicators
                # TS uses: ✓, …, ✗. Added * just in case.
                tool_name_candidate = re.sub(r"^[✓✗…*]?\s*", "", tool_name_with_status)

                # 4. Remove "(from extension_name)" suffix
                tool_name_candidate = re.sub(
                    r"\s*\(from\s+.*\)", "", tool_name_candidate
                ).strip()

                if tool_name_candidate:
                    tools.append(tool_name_candidate)
        except Exception as e:
            logging.warning(f"Failed to list MCP tools: {e}")

        return list(set(tools))

    async def get_gemini_cli_extensions(self) -> list[str]:
        """Returns a list of available Gemini CLI extensions."""
        if not self._setup_completed:
            raise RuntimeError(
                f"Generator {self.name} has not been set up. Please call setup() first."
            )
        extensions = []

        # 2. List Extensions
        # TODO: The gemini CLI often returns LLM-generated explanations instead of raw tool lists.
        # This requires a more robust parsing strategy or a way to force raw CLI output.
        # The current parsing relies on specific plain-text formatting which is unreliable.
        # TODO: Explain why there are two output formats in extreme detail.
        # Output format: "✓ adk-docs-ext (v...)" or just "adk-docs-ext"
        try:
            ext_res, _ = await self.run_cli_command(
                [self.cli_path, "extensions", "list"]
            )
            for line in ext_res.get("stdout", "").splitlines():
                # 1. Strip ANSI first so we can reliably check indentation
                clean_line = self._strip_ansi(line)

                # 2. Structural Check:
                # TS Output: "\n ID:..." -> This results in a line starting with a space.
                # We skip indented lines to ignore details.
                if clean_line.startswith(" ") or clean_line.startswith("\t"):
                    continue

                stripped = clean_line.strip()

                # 3. Content Check (Redundant safety net, but good to keep)
                if (
                    not stripped
                    or stripped.lower().startswith("error")
                    or "no extensions installed" in stripped.lower()
                ):
                    continue

                # 4. Regex extraction
                # TS Output: "✓ extension-name (version)"
                # We allow for alphanumeric, underscores, dashes, and @/ (for scoped packages)
                match = re.search(
                    r"^[✓✗…*]?\s*([ @a-zA-Z0-9_/-]+)(?:\s*\(.*\))?", stripped
                )
                if match:
                    extensions.append(match.group(1).strip())
        except Exception as e:
            logging.warning(f"Failed to list Gemini CLI extensions: {e}")

        return list(set(extensions))

    def _extract_json_from_text(self, text: str) -> str:
        """Extracts JSON content from a string, handling markdown code blocks."""
        text = text.strip()

        # Match ```json ... ``` or just ``` ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1)

        # If no code blocks, assume the whole text is JSON
        return text

    def _strip_ansi(self, text: str) -> str:
        """Removes ANSI escape codes from string."""
        return re.sub(r"\x1b\[[0-9;]*m", "", text)
