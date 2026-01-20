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

"""An AnswerGenerator that uses the Gemini API to generate answers."""

import hashlib
from pathlib import Path

from benchmarks.answer_generators.llm_base import LlmAnswerGenerator
from benchmarks.data_models import BaseBenchmarkCase, ApiUnderstandingAnswerOutput, ApiUnderstandingBenchmarkCase, FixErrorAnswerOutput, FixErrorBenchmarkCase, GeneratedAnswer, MultipleChoiceAnswerOutput, MultipleChoiceBenchmarkCase, TraceLogEvent, TraceEventType, UsageMetadata, BenchmarkGenerationError
from benchmarks.api_key_manager import API_KEY_MANAGER, ApiKeyManager, KeyType
from google import genai


class GeminiAnswerGenerator(LlmAnswerGenerator):
    """
    An AnswerGenerator that uses the Gemini API.
    """

    def __init__(self, model_name: str, context: str, api_key_manager: ApiKeyManager):
        super().__init__()
        self.model_name = model_name
        self.context = context
        self.api_key_manager = api_key_manager
        self.client = None # Initialized in _async_init

    async def _async_init(self):
        """Asynchronous part of initialization."""
        api_key = await self.api_key_manager.get_next_key(KeyType.GEMINI_API)
        self.client = genai.Client(api_key=api_key).aio
        return self

    @classmethod
    async def create(cls, model_name: str, context: str, api_key_manager: ApiKeyManager):
        """Async factory for creating an instance."""
        instance = cls(model_name, context, api_key_manager)
        return await instance._async_init()

    @property
    def name(self) -> str:
        """Returns a unique name for this generator instance."""
        base_name = f"GeminiAnswerGenerator({self.model_name})"
        if self.context:
            if isinstance(self.context, Path):
                # Use the file name if context is a Path
                return f"{base_name}-with-context-{self.context.name}"
            elif isinstance(self.context, str):
                # For string context, always use a stable hash
                context_id = self.context.strip()
                if context_id:
                    context_hash_digest = hashlib.md5(
                        context_id.encode("utf-8")
                    ).hexdigest()[:8]
                    return f"{base_name}-with-context-hash-{context_hash_digest}"
        return base_name

    @property
    def description(self) -> str:
        """Returns a detailed description of the generator."""
        desc = f"**Model:** {self.model_name}\n\n"
        desc += "**Type:** Gemini API (Direct Structured Output)\n\n"
        
        context_content = self._get_context_content()
        if context_content:
            preview = context_content[:200]
            desc += f"**Context Preview:**\n> {preview}..."
            
        return desc

    async def generate_answer(
        self, benchmark_case: BaseBenchmarkCase, run_id: str
    ) -> GeneratedAnswer:
        """Generates an answer using the Gemini API's structured output feature."""
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
            raise TypeError(f"Unsupported benchmark case type: {type(benchmark_case)}")

        json_schema = response_schema.model_json_schema()

        # Remove benchmark_type from schema to prevent LLM confusion
        if (
            "properties" in json_schema
            and "benchmark_type" in json_schema["properties"]
        ):
            del json_schema["properties"]["benchmark_type"]
        if "required" in json_schema and "benchmark_type" in json_schema["required"]:
            json_schema["required"].remove("benchmark_type")

        # Retrieve API Key for this run
        if not self.api_key_manager:
            raise RuntimeError("ApiKeyManager is not configured for GeminiAnswerGenerator.")

        api_key, key_id = await self.api_key_manager.get_key_for_run(run_id, KeyType.GEMINI_API)
        if not api_key:
            raise RuntimeError(f"No API key available for run_id '{run_id}' from ApiKeyManager.")

        client = genai.Client(api_key=api_key).aio

        try:
            response = await client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": json_schema,
                },
            )
            await self.api_key_manager.report_result(
                KeyType.GEMINI_API, key_id, success=True
            )

        except Exception as e:
            await self.api_key_manager.report_result(
                KeyType.GEMINI_API, key_id, success=False, error_message=str(e)
            )
            raise BenchmarkGenerationError(f"Gemini API Generation failed: {e}", original_exception=e, api_key_id=key_id) from e
        finally:
            self.api_key_manager.release_run(run_id)

        output = response_schema.model_validate_json(response.text)

        # Populate trace_logs with the full response metadata (usage, safety ratings, etc.)
        trace_logs = [
            TraceLogEvent(
                type=TraceEventType.GEMINI_API_RESPONSE,
                content=response.text,
                details=response.model_dump(mode='json'),
            )
        ]

        usage_metadata = None
        if response.usage_metadata:
            usage_metadata = UsageMetadata(
                total_tokens=response.usage_metadata.total_token_count,
                prompt_tokens=response.usage_metadata.prompt_token_count,
                completion_tokens=response.usage_metadata.candidates_token_count,
            )

        return GeneratedAnswer(
            output=output,
            trace_logs=trace_logs,
            usage_metadata=usage_metadata,
            api_key_id=key_id,
        )
