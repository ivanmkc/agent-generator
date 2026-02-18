import asyncio
import json
from typing import Any, Optional

import aiohttp
from benchmarks.answer_generators.llm_base import LlmAnswerGenerator
from benchmarks.data_models import (
    ApiUnderstandingAnswerOutput,
    ApiUnderstandingBenchmarkCase,
    BaseBenchmarkCase,
    FixErrorAnswerOutput,
    FixErrorBenchmarkCase,
    GeneratedAnswer,
    MultipleChoiceAnswerOutput,
    MultipleChoiceBenchmarkCase,
    TraceLogEvent,
    UsageMetadata,
    BenchmarkGenerationError,
)
from core.api_key_manager import ApiKeyManager, KeyType
from benchmarks.answer_generators.gemini_cli_docker.podman_utils import PodmanContainer

class ClaudeCliPodmanAnswerGenerator(LlmAnswerGenerator):
    """
    An AnswerGenerator that uses a LiteLLM server in a podman container to call Claude via Vertex AI.
    """

    def __init__(
        self,
        model_name: str,
        api_key_manager: ApiKeyManager,
        image_name: str,
        image_definitions: dict[str, Any],
        context_instruction: Optional[str] = None,
    ):
        super().__init__(context=context_instruction, api_key_manager=api_key_manager)
        self.model_name = model_name
        self.image_name = image_name
        self.context_instruction = context_instruction
        self.container = PodmanContainer(
            image_name=image_name,
            image_definitions=image_definitions,
        )
        self._setup_lock = asyncio.Lock()
        self._setup_completed = False

    @property
    def name(self) -> str:
        return f"ClaudeCliPodmanAnswerGenerator({self.model_name}, image={self.image_name})"

    @property
    def description(self) -> str:
        return f"Answer generator using {self.model_name} via a LiteLLM server in a Podman container ({self.image_name})."

    async def setup(self, force_deploy: bool = False) -> None:
        async with self._setup_lock:
            if self._setup_completed:
                return
            await self.container.start(force_build=force_deploy)
            self._setup_completed = True

    async def teardown(self) -> None:
        if self.container:
            self.container.stop()

    async def generate_answer(
        self,
        benchmark_case: BaseBenchmarkCase,
        run_id: str,
    ) -> GeneratedAnswer:
        prompt: str
        response_schema: Any | None = None

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
        
        schema_json = None
        if response_schema:
            schema_json = response_schema.model_json_schema()
            if "properties" in schema_json and "benchmark_type" in schema_json["properties"]:
                del schema_json["properties"]["benchmark_type"]
            if "required" in schema_json and "benchmark_type" in schema_json["required"]:
                schema_json["required"].remove("benchmark_type")

        messages = [{"role": "user", "content": prompt}]
        if self.context_instruction:
            messages.insert(0, {"role": "system", "content": self.context_instruction})

        payload = {
            "model": self.model_name,
            "messages": messages,
        }
        if schema_json:
            payload["response_schema"] = schema_json
        
        logs = [TraceLogEvent(type="REQUEST_PAYLOAD", source=self.name, content=json.dumps(payload, indent=2))]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.container.base_url}/completion", json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise BenchmarkGenerationError(f"Claude container returned {resp.status}: {error_text}", trace_logs=logs)
                    
                    response_data = await resp.json()
            
            logs.append(TraceLogEvent(type="RESPONSE_PAYLOAD", source=self.name, content=json.dumps(response_data, indent=2)))

            # Extract content from litellm response
            message_content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Handle structured output from litellm
            tool_calls = response_data.get("choices", [{}])[0].get("message", {}).get("tool_calls")
            if tool_calls:
                # The actual arguments from the tool call contain the structured JSON
                message_content = tool_calls[0].get("function", {}).get("arguments", "{}")


            output = response_schema.model_validate_json(message_content)

            usage = response_data.get("usage", {})
            usage_metadata = UsageMetadata(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
            return GeneratedAnswer(
                output=output,
                raw_output=message_content,
                trace_logs=logs,
                usage_metadata=usage_metadata,
            )

        except Exception as e:
            raise BenchmarkGenerationError(f"Claude generation failed: {e}", original_exception=e, trace_logs=logs) from e
