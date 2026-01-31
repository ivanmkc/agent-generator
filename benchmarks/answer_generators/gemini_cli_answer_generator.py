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
from typing import Any, Optional


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
from core.trace_utils import parse_cli_stream_json_output
from pydantic import BaseModel
from core.api_key_manager import ApiKeyManager, KeyType
from benchmarks.answer_generators.gemini_answer_generator import GeminiAnswerGenerator


class GeminiCliExecutionError(Exception):
    """Exception raised when the Gemini CLI execution fails, preserving logs."""

    def __init__(
        self,
        message: str,
        logs: list[TraceLogEvent],
        response_dict: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.logs = logs
        self.response_dict = response_dict


class GeminiCliAnswerGenerator(GeminiAnswerGenerator):
    """
    An AnswerGenerator that uses the gemini-cli tool.
    """

    def __init__(
        self,
        model_name: str,
        context: str,
        api_key_manager: ApiKeyManager,
    ):
        super().__init__(
            model_name=model_name, context=context, api_key_manager=api_key_manager
        )
        self.cli_path = "gemini"

    @classmethod
    async def create(
        cls,
        model_name: str,
        context: str,
        api_key_manager: ApiKeyManager,
    ):
        """Async factory for creating an instance."""
        # This class doesn't have its own async init, so we just call the superclass create
        # But we need to call __init__ first, then _async_init.
        # The base class `create` method handles this.
        instance = cls(model_name, context, api_key_manager)
        await super(GeminiCliAnswerGenerator, instance)._async_init()
        return instance

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
            raise RuntimeError(
                "ApiKeyManager is not configured for GeminiCliAnswerGenerator."
            )

        current_key, api_key_id = await self.api_key_manager.get_key_for_run(
            run_id, KeyType.GEMINI_API
        )
        if not current_key:
            raise RuntimeError(
                f"No API key available for run_id '{run_id}' from ApiKeyManager."
            )

        extra_env["GEMINI_API_KEY"] = current_key

        try:
            # Run the CLI command
            cli_response_dict, logs = await self.run_cli_command(
                command_parts, extra_env=extra_env
            )

            # Report success
            await self.api_key_manager.report_result(
                KeyType.GEMINI_API, api_key_id, success=True
            )
            # Note: We don't easily detect 429s from CLI text output here unless we parse logs deeply.
            # Assuming CLI handles retries or we catch generic failures.

        except GeminiCliExecutionError as e:
            # Report Failure
            await self.api_key_manager.report_result(
                KeyType.GEMINI_API, api_key_id, success=False, error_message=str(e)
            )
            raise BenchmarkGenerationError(
                f"Gemini CLI Generation failed: {e}",
                original_exception=e,
                api_key_id=api_key_id,
                trace_logs=e.logs,
            ) from e
        except Exception as e:
            # Report Failure
            await self.api_key_manager.report_result(
                KeyType.GEMINI_API, api_key_id, success=False, error_message=str(e)
            )
            raise BenchmarkGenerationError(
                f"Gemini CLI Generation failed: {e}",
                original_exception=e,
                api_key_id=api_key_id,
            ) from e
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
            await self.api_key_manager.report_result(
                KeyType.GEMINI_API, api_key_id, success=False
            )

            # If parsing fails, raise BenchmarkGenerationError to preserve logs
            raise BenchmarkGenerationError(
                f"Failed to parse structured output from CLI response: {e}\nOutput was: {model_text}",
                original_exception=e,
                api_key_id=api_key_id,
                trace_logs=logs,
            ) from e

        usage_metadata = None

        if "stats" in cli_response_dict:
            stats = cli_response_dict["stats"]
            usage_metadata = UsageMetadata(
                total_tokens=stats.get("total_token_count")
                or stats.get("total_tokens"),
                prompt_tokens=stats.get("prompt_token_count")
                or stats.get("input_tokens"),
                completion_tokens=stats.get("candidates_token_count")
                or stats.get("output_tokens"),
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
        extra_env: dict[str, str] = None,  # Added argument
    ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
        """Executes the gemini CLI command and returns the parsed JSON output and raw logs.

        This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement run_cli_command")

    async def setup(self, force_deploy: bool = False) -> None:
        """Performs any necessary setup (e.g., starting containers)."""
        self._setup_completed = True

    async def get_mcp_servers(self) -> list[str]:
        """Returns a list of available MCP servers."""
        if not self._setup_completed:
            raise RuntimeError(
                f"Generator {self.name} has not been set up. Please call setup() first."
            )
        servers = []

        try:
            mcp_res, _ = await self.run_cli_command([self.cli_path, "mcp", "list"])
            # The CLI sometimes prints to stderr (e.g. 0.26.0), so we check both
            output = mcp_res.get("stdout", "") + "\n" + mcp_res.get("stderr", "")
            
            for line in output.splitlines():
                # 1. Clean the line of ANSI codes immediately
                clean_line = self._strip_ansi(line).strip()

                if (
                    not clean_line
                    or clean_line == "Configured MCP servers:"
                    or clean_line == "(none)"
                ):
                    continue

                # 2. Extract Server Name
                # Output formats:
                # "✓ server-name (transport) - status"
                # "✓ server-name (from ...): tool1, tool2"

                # Strip leading checkmarks/dots
                clean_line = re.sub(r"^[✓✗…*]?\s*", "", clean_line)

                # Extract the server name (everything before the first parenthesis or colon)
                # Matches "server-name" in "server-name (stdio)..."
                match = re.search(r"^([^\(\:]+)", clean_line)
                if match:
                    server_name = match.group(1).strip()
                    if server_name:
                        servers.append(server_name)

        except Exception as e:
            logging.warning(f"Failed to list MCP servers: {e}")

        return list(set(servers))

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
        """Extracts JSON content from a string, handling markdown code blocks and conversational wrappers."""
        text = text.strip()

        # 1. Try to find code blocks
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 2. If no code blocks, try to find the first JSON object
        # Look for first '{' and last '}'
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]

        # Fallback: return original text
        return text

    def _strip_ansi(self, text: str) -> str:
        """Removes ANSI escape codes from string."""
        return re.sub(r"\x1b\[[0-9;]*m", "", text)
