import uuid
import time
import datetime # Added import
from typing import Optional, Callable, Awaitable
import os # Added import

from google.adk.agents import Agent
from google.adk.apps import App # Added import for App
from google.adk.runners import InMemoryRunner
from google.genai import types

from benchmarks.answer_generators.llm_base import LlmAnswerGenerator
from benchmarks.data_models import BaseBenchmarkCase, ApiUnderstandingAnswerOutput, ApiUnderstandingBenchmarkCase, FixErrorAnswerOutput, FixErrorBenchmarkCase, GeneratedAnswer, MultipleChoiceAnswerOutput, MultipleChoiceBenchmarkCase, TraceLogEvent, TraceEventType, UsageMetadata
from benchmarks.api_key_manager import ApiKeyManager


class AdkAnswerGenerator(LlmAnswerGenerator):
    """
    An AnswerGenerator that uses an ADK Agent.
    It acts as a generic runner for any provided ADK Agent.
    """

    def __init__(
        self,
        agent: Agent,
        name: str | None = None,
        setup_hook: Optional[Callable[[], Awaitable[None]]] = None,
        teardown_hook: Optional[Callable[[], Awaitable[None]]] = None,
        api_key_manager: ApiKeyManager | None = None,
    ):
        super().__init__(context=None)
        self.agent = agent
        self.api_key_manager = api_key_manager
        self.setup_hook = setup_hook
        self.teardown_hook = teardown_hook
        # Explicitly create an App instance to control its name
        self.app = App(name=f"AdkBenchmarkApp_{self.agent.name}_{uuid.uuid4().hex}", root_agent=self.agent)
        self.runner = InMemoryRunner(app=self.app) # Pass the App instance
        self._name = name or f"AdkAnswerGenerator({self.agent.name})"

    @property
    def name(self) -> str:
        """Returns a unique name for this generator instance."""
        return self._name

    async def setup(self, force_deploy: bool = False) -> None:
        """Executes the optional setup hook."""
        if self.setup_hook:
            await self.setup_hook()

    async def teardown(self) -> None:
        """Executes the optional teardown hook."""
        if self.teardown_hook:
            await self.teardown_hook()

    async def generate_answer(
        self, benchmark_case: BaseBenchmarkCase
    ) -> GeneratedAnswer:
        """Generates an answer using the ADK Agent."""

        if isinstance(benchmark_case, FixErrorBenchmarkCase):
            prompt = self._create_prompt_for_fix_error(benchmark_case)
            output_schema_class = FixErrorAnswerOutput
        elif isinstance(benchmark_case, ApiUnderstandingBenchmarkCase):
            prompt = self._create_prompt_for_api_understanding(benchmark_case)
            output_schema_class = ApiUnderstandingAnswerOutput
        elif isinstance(benchmark_case, MultipleChoiceBenchmarkCase):
            prompt = self._create_prompt_for_multiple_choice(benchmark_case)
            output_schema_class = MultipleChoiceAnswerOutput
        else:
            raise TypeError(f"Unsupported benchmark case type: {type(benchmark_case)}")

        # Run the agent asynchronously.
        response_text, trace_logs, usage_metadata = await self._run_agent_async(prompt)

        # Extract JSON from markdown code block if present
        if "```json" in response_text:
            json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
        else:
            json_str = response_text.strip()

        # Parse the JSON response into the appropriate Pydantic model.
        # This will raise a ValidationError if the schema doesn't match.
        output = output_schema_class.model_validate_json(json_str)
        
        # Resolve API Key ID
        api_key_id = None
        if self.api_key_manager:
            current_key = os.environ.get("GEMINI_API_KEY")
            if current_key:
                api_key_id = self.api_key_manager.get_key_id(current_key)

        return GeneratedAnswer(
            output=output, 
            trace_logs=trace_logs, 
            usage_metadata=usage_metadata,
            api_key_id=api_key_id
        )

    async def _run_agent_async(
        self, prompt: str
    ) -> tuple[str, list[TraceLogEvent], UsageMetadata]:
        """Helper to run the agent and get the response."""
        if not self.runner:
            raise RuntimeError("ADK runner not initialized. Call setup() first.")

        session_id = f"benchmark_session_{uuid.uuid4()}"
        session = await self.runner.session_service.create_session(
            app_name=self.app.name, # Use self.app.name here
            user_id="benchmark_user",
            session_id=session_id,
        )
        final_response = ""
        logs: list[TraceLogEvent] = []

        # Explicitly log the initial prompt as a user message
        logs.append(
            TraceLogEvent(
                type=TraceEventType.MESSAGE,
                source="adk",
                timestamp=datetime.datetime.now().isoformat(),
                role="user",
                author="system",  # Indicates it's the initial system/user prompt
                content=prompt,
                details={"step": "Initial Prompt to Agent"}
            )
        )

        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0

        new_message = types.UserContent(parts=[types.Part(text=prompt)])

        async for event in self.runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=new_message
        ):
            # Extract usage metadata if available
            if hasattr(event, "usage_metadata") and event.usage_metadata:
                # Note: ADK usage_metadata attributes might vary, assuming standard keys
                # We try to get attributes safely
                pmt = getattr(event.usage_metadata, "prompt_token_count", 0) or 0
                cpt = getattr(event.usage_metadata, "candidates_token_count", 0) or 0
                tt = getattr(event.usage_metadata, "total_token_count", 0) or 0

                total_prompt_tokens += pmt
                total_completion_tokens += cpt
                total_tokens += tt

            # Base details for the event
            base_details = event.model_dump(mode='json')
            timestamp = (
                event.created_time.isoformat()
                if hasattr(event, "created_time") and event.created_time
                else None
            )

            # Attempt to extract common fields that might be present directly on the ADK event
            event_tool_name = getattr(event, "tool_name", None)
            event_agent_name = getattr(event, "agent_name", None)

            # Analyze content parts to generate specific log events
            events_generated = False
            if event.content and event.content.parts:
                for part in event.content.parts:
                    # 1. Text (Model Response or User Message)
                    if part.text:
                        log_event = TraceLogEvent(
                            type=TraceEventType.MESSAGE,
                            source="adk",
                            timestamp=timestamp,
                            role=event.content.role,
                            author=event_agent_name or event.author,
                            content=part.text,
                            details=base_details
                        )
                        logs.append(log_event)
                        events_generated = True

                    # 2. Function Call (Tool Use)
                    if part.function_call:
                        log_event = TraceLogEvent(
                            type=TraceEventType.TOOL_USE,
                            source="adk",
                            timestamp=timestamp,
                            role="model",
                            author=event_agent_name or event.author,
                            tool_name=event_tool_name or part.function_call.name,
                            tool_input=part.function_call.args, # Assuming args is dict/json-serializable
                            tool_call_id=getattr(part.function_call, "id", None),
                            details=base_details
                        )
                        logs.append(log_event)
                        events_generated = True

                    # 3. Function Response (Tool Result)
                    if part.function_response:
                        response_content = part.function_response.response
                        # Simplify response if it's just a 'result' key
                        if isinstance(response_content, dict) and "result" in response_content and len(response_content) == 1:
                            tool_output_str = str(response_content["result"])
                        else:
                            tool_output_str = str(response_content)

                        log_event = TraceLogEvent(
                            type=TraceEventType.TOOL_RESULT,
                            source="adk",
                            timestamp=timestamp,
                            role="tool",
                            author=event_agent_name or event.author,
                            tool_name=event_tool_name or part.function_response.name,
                            tool_output=tool_output_str,
                            tool_call_id=getattr(part.function_response, "id", None),
                            details=base_details
                        )
                        logs.append(log_event)
                        events_generated = True

            # Fallback for ADK internal events (e.g., sub-agent orchestration)
            if not events_generated:
                content_text = None
                if getattr(event, "content", None) and event.content.parts:
                    content_text = "".join([p.text for p in event.content.parts if p.text])

                log_event = TraceLogEvent(
                    type=TraceEventType.ADK_EVENT,
                    source="adk",
                    timestamp=timestamp,
                    role=getattr(event, "role", None), # ADK events might have a role directly
                    author=event_agent_name or event.author,
                    tool_name=event_tool_name,
                    content=content_text,
                    details=base_details,
                )
                logs.append(log_event)

            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                # Continue consuming the stream to allow subsequent agents in a sequence to run.
                # The final_response variable will be updated with the last response.
                
        
        usage_metadata = UsageMetadata(
            total_tokens=total_tokens,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
        )

        return final_response, logs, usage_metadata

