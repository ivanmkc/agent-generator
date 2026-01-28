"""Adk Answer Generator module."""

import uuid
import time
import datetime
from typing import Optional, Callable, Awaitable, List, Dict, Any
import os

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.runners import InMemoryRunner
from google.genai import types

from benchmarks.answer_generators.llm_base import LlmAnswerGenerator
from benchmarks.data_models import (
    BaseBenchmarkCase,
    ApiUnderstandingAnswerOutput,
    ApiUnderstandingBenchmarkCase,
    FixErrorAnswerOutput,
    FixErrorBenchmarkCase,
    GeneratedAnswer,
    MultipleChoiceAnswerOutput,
    MultipleChoiceBenchmarkCase,
    TraceLogEvent,
    TraceEventType,
    UsageMetadata,
    BenchmarkGenerationError,
)
from core.api_key_manager import ApiKeyManager, KeyType
from benchmarks.answer_generators.adk_context import adk_execution_context


from google.adk.plugins.base_plugin import BasePlugin
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.base_agent import BaseAgent
from google.adk.events.event import Event


class TraceCollectorPlugin(BasePlugin):
    """
    An ADK Plugin that collects trace events and usage metadata during an invocation.
    """

    def __init__(self, name: str = "trace_collector"):
        super().__init__(name=name)
        self.logs: List[TraceLogEvent] = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.execution_sequence = []
        self._current_agent = None
        self._current_agent_start = time.time()
        self._current_agent_prompt_tokens = 0
        self._current_agent_completion_tokens = 0

    async def on_user_message_callback(
        self, *, invocation_context: InvocationContext, user_message: types.Content
    ) -> Optional[types.Content]:
        """Log the initial user message."""
        timestamp = datetime.datetime.now().isoformat()
        if user_message and user_message.parts:
            content = "".join([p.text for p in user_message.parts if p.text])
            self.logs.append(
                TraceLogEvent(
                    type=TraceEventType.MESSAGE,
                    source="adk",
                    timestamp=timestamp,
                    role="user",
                    author="user",
                    content=content,
                    details={"step": "Initial User Prompt"},
                )
            )
        return None

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        now = time.time()
        if self._current_agent:
            self.execution_sequence.append(
                {
                    "agent": self._current_agent,
                    "duration": now - self._current_agent_start,
                    "prompt_tokens": self._current_agent_prompt_tokens,
                    "completion_tokens": self._current_agent_completion_tokens,
                }
            )

        self._current_agent = agent.name
        self._current_agent_start = now
        self._current_agent_prompt_tokens = 0
        self._current_agent_completion_tokens = 0
        return None

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        timestamp = datetime.datetime.now().isoformat()
        agent_name = callback_context.agent_name

        # 1. Capture System Instruction
        prompt_parts = []
        if llm_request.config and llm_request.config.system_instruction:
            si = llm_request.config.system_instruction
            # TODO: Avoid hasattr and use proper interfaces if possible
            if hasattr(si, "parts"):
                si_text = "".join([p.text for p in si.parts if p.text])
            else:
                si_text = str(si)
            prompt_parts.append(f"--- System Instruction ---\n{si_text}")

        # 2. Capture User/History Content
        if llm_request.contents:
            prompt_parts.append(
                f"--- Context/History ({len(llm_request.contents)} items) ---"
            )
            last_msg = llm_request.contents[-1]
            if last_msg.parts:
                last_text = "".join([p.text for p in last_msg.parts if p.text])
                prompt_parts.append(f"Last Message ({last_msg.role}): {last_text}")

        full_prompt = "\n\n".join(prompt_parts)

        self.logs.append(
            TraceLogEvent(
                type=TraceEventType.ADK_EVENT,  # Using generic event for Prompt Input
                source="adk",
                timestamp=timestamp,
                role="system",
                author=agent_name,
                content=full_prompt,
                details={"step": "LLM Input (Prompt)", "model": llm_request.model},
            )
        )
        return None

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        if llm_response.usage_metadata and not llm_response.partial:
            pmt = llm_response.usage_metadata.prompt_token_count or 0
            cpt = llm_response.usage_metadata.candidates_token_count or 0
            tt = llm_response.usage_metadata.total_token_count or 0

            self.total_prompt_tokens += pmt
            self.total_completion_tokens += cpt
            self.total_tokens += tt

            self._current_agent_prompt_tokens += pmt
            self._current_agent_completion_tokens += cpt
        return None

    async def on_event_callback(
        self, *, invocation_context: InvocationContext, event: Event
    ) -> Optional[Event]:
        timestamp = (
            event.created_time.isoformat()
            if hasattr(event, "created_time") and event.created_time
            else datetime.datetime.now().isoformat()
        )
        author = event.author or "unknown"

        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    self.logs.append(
                        TraceLogEvent(
                            type=TraceEventType.MESSAGE,
                            source="adk",
                            timestamp=timestamp,
                            role=event.content.role,
                            author=author,
                            content=part.text,
                            details=event.model_dump(mode="json"),
                        )
                    )
                if part.function_call:
                    self.logs.append(
                        TraceLogEvent(
                            type=TraceEventType.TOOL_USE,
                            source="adk",
                            timestamp=timestamp,
                            role="model",
                            author=author,
                            tool_name=part.function_call.name,
                            tool_input=part.function_call.args,
                            tool_call_id=part.function_call.id,
                            details=event.model_dump(mode="json"),
                        )
                    )
                if part.function_response:
                    resp = part.function_response.response
                    tool_output_str = (
                        str(resp.get("result", resp))
                        if isinstance(resp, dict)
                        else str(resp)
                    )
                    self.logs.append(
                        TraceLogEvent(
                            type=TraceEventType.TOOL_RESULT,
                            source="adk",
                            timestamp=timestamp,
                            role="tool",
                            author=author,
                            tool_name=part.function_response.name,
                            tool_output=tool_output_str,
                            tool_call_id=part.function_response.id,
                            details=event.model_dump(mode="json"),
                        )
                    )
        return None

    def finalize(self):
        """Adds the final agent block to the sequence."""
        if self._current_agent:
            self.execution_sequence.append(
                {
                    "agent": self._current_agent,
                    "duration": time.time() - self._current_agent_start,
                    "prompt_tokens": self._current_agent_prompt_tokens,
                    "completion_tokens": self._current_agent_completion_tokens,
                }
            )


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
        model_name: str | None = None,
    ):
        super().__init__(context=None)
        self.agent = agent
        self.api_key_manager = api_key_manager
        self.setup_hook = setup_hook
        self.teardown_hook = teardown_hook

        self._name = name or f"AdkBenchmarkGenerator_{uuid.uuid4().hex}"
        self.model_name = model_name or "Unknown"
        if self.model_name == "Unknown" and hasattr(agent, "model"):
            m = agent.model
            if isinstance(m, str):
                self.model_name = m
            elif hasattr(m, "model"):
                self.model_name = getattr(m, "model", "Unknown")

    @property
    def name(self) -> str:
        """Returns a unique name for this generator instance."""
        return self._name

    @property
    def description(self) -> str:
        """Returns a detailed description of the generator and its agent workflow."""
        agent = self.agent

        model_str = "Unknown"
        # TODO: Avoid hasattr and use proper interfaces if possible
        if hasattr(agent, "model"):
            m = agent.model
            if isinstance(m, str):
                model_str = m
            elif hasattr(m, "model"):
                model_str = getattr(m, "model", "Unknown")

        desc = f"**Model:** {model_str}\n\n"

        # TODO: Avoid hasattr and use proper interfaces if possible
        if hasattr(agent, "sub_agents") and agent.sub_agents:
            steps = []
            for sa in agent.sub_agents:
                name = getattr(sa, "name", type(sa).__name__)
                steps.append(f"`{name}`")
            desc += f"**Multi-Agent Workflow:** {' → '.join(steps)}\n\n"
        else:
            # TODO: Avoid hasattr and use proper interfaces if possible
            agent_name = getattr(agent, "name", type(agent).__name__)
            desc += f"**Agent:** `{agent_name}` (Single Agent)\n\n"

        # TODO: Avoid hasattr and use proper interfaces if possible
        if hasattr(agent, "instruction") and agent.instruction:
            instr = agent.instruction
            if isinstance(instr, str):
                if len(instr) > 300:
                    instr = instr[:300] + "..."
                desc += f"**System Instruction:**\n> {instr}\n\n"

        return desc

    async def setup(self, force_deploy: bool = False) -> None:
        """Executes the optional setup hook."""
        if self.setup_hook:
            await self.setup_hook()

    async def teardown(self) -> None:
        """Executes the optional teardown hook."""
        if self.teardown_hook:
            await self.teardown_hook()

    async def generate_answer(
        self,
        benchmark_case: BaseBenchmarkCase,
        run_id: str,
    ) -> GeneratedAnswer:
        """Generates an answer using the ADK Agent."""

        if isinstance(benchmark_case, FixErrorBenchmarkCase):
            prompt = self._create_prompt_for_fix_error(benchmark_case)
            output_schema_class = FixErrorAnswerOutput
            benchmark_type = "fix_error"
        elif isinstance(benchmark_case, ApiUnderstandingBenchmarkCase):
            prompt = self._create_prompt_for_api_understanding(benchmark_case)
            output_schema_class = ApiUnderstandingAnswerOutput
            benchmark_type = "api_understanding"
        elif isinstance(benchmark_case, MultipleChoiceBenchmarkCase):
            prompt = self._create_prompt_for_multiple_choice(benchmark_case)
            output_schema_class = MultipleChoiceAnswerOutput
            benchmark_type = "multiple_choice"
        else:
            raise TypeError(f"Unsupported benchmark case type: {type(benchmark_case)}")

        api_key_id: Optional[str] = None
        token = None
        current_key = None

        if self.api_key_manager:
            current_key, api_key_id = await self.api_key_manager.get_key_for_run(
                run_id, KeyType.GEMINI_API
            )

        token = adk_execution_context.set(
            {"api_key": current_key, "key_id": api_key_id}
        )

        trace_logs = None
        usage_metadata = None

        try:
            response_text, trace_logs, usage_metadata, _ = await self._run_agent_async(
                prompt, api_key_id=api_key_id, benchmark_type=benchmark_type
            )

            if "```json" in response_text:
                json_str = (
                    response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                )
            else:
                json_str = response_text.strip()

            try:
                output = output_schema_class.model_validate_json(json_str)
            except Exception:
                # Return raw output to let the benchmark runner handle sanitization/validation
                if self.api_key_manager:
                    await self.api_key_manager.report_result(
                        KeyType.GEMINI_API, api_key_id, success=True
                    )

                return GeneratedAnswer(
                    output=None,
                    raw_output=response_text,
                    trace_logs=trace_logs,
                    usage_metadata=usage_metadata,
                    api_key_id=api_key_id,
                )

            if self.api_key_manager:
                await self.api_key_manager.report_result(
                    KeyType.GEMINI_API, api_key_id, success=True
                )

            return GeneratedAnswer(
                output=output,
                trace_logs=trace_logs,
                usage_metadata=usage_metadata,
                api_key_id=api_key_id,
            )

        except Exception as e:
            if self.api_key_manager:
                await self.api_key_manager.report_result(
                    KeyType.GEMINI_API, api_key_id, success=False, error_message=str(e)
                )

            if isinstance(e, BenchmarkGenerationError):
                raise e

            raise BenchmarkGenerationError(
                f"ADK Generation failed: {e}",
                original_exception=e,
                api_key_id=api_key_id,
                trace_logs=trace_logs,
                usage_metadata=usage_metadata,
            ) from e

        finally:
            if token:
                adk_execution_context.reset(token)

    async def _run_agent_async(
        self,
        prompt: str,
        api_key_id: Optional[str] = None,
        benchmark_type: str = "unknown",
    ) -> tuple[str, list[TraceLogEvent], UsageMetadata, str]:
        """Helper to run the agent using a fresh Runner and TraceCollectorPlugin."""

        # TODO: Avoid hasattr and use proper interfaces if possible
        if getattr(self.agent, "__module__", "").startswith("google.adk.agents"):
            app_name = "agents"
        else:
            app_name = f"AdkBenchmarkApp_{getattr(self.agent, 'name', 'unnamed')}_{uuid.uuid4().hex}"

        collector = TraceCollectorPlugin()
        app = App(name=app_name, root_agent=self.agent, plugins=[collector])
        runner = InMemoryRunner(app=app)

        session_id = f"benchmark_session_{uuid.uuid4()}"
        session = await runner.session_service.create_session(
            app_name=app.name,
            user_id="benchmark_user",
            session_id=session_id,
            state={"benchmark_type": benchmark_type},
        )

        collector.logs.append(
            TraceLogEvent(
                type=TraceEventType.MESSAGE,
                source="adk",
                timestamp=datetime.datetime.now().isoformat(),
                role="user",
                author="system",
                content=prompt,
                details={"step": "Initial Prompt to Agent"},
            )
        )

        final_response = ""
        new_message = types.UserContent(
            parts=[types.Part(text=f"Task Type: {benchmark_type}\n\n{prompt}")]
        )

        try:
            async for event in runner.run_async(
                user_id=session.user_id, session_id=session.id, new_message=new_message
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response = "".join(
                            [p.text for p in event.content.parts if p.text]
                        )
        except Exception as e:
            collector.finalize()
            partial_usage = UsageMetadata(
                total_tokens=collector.total_tokens,
                prompt_tokens=collector.total_prompt_tokens,
                completion_tokens=collector.total_completion_tokens,
            )
            raise BenchmarkGenerationError(
                f"ADK Run Failed: {e}",
                original_exception=e,
                api_key_id=api_key_id,
                trace_logs=collector.logs,
                usage_metadata=partial_usage,
            ) from e

        collector.finalize()

        loop_exit_reason = "Max Iterations Reached (Implicit)"
        loop_iterations = sum(
            1
            for e in collector.logs
            if e.type == TraceEventType.MESSAGE and e.author == "run_analysis_agent"
        )

        for e in collector.logs:
            if e.type == TraceEventType.TOOL_USE and e.tool_name == "exit_loop":
                loop_exit_reason = "Analyst Exited (Explicit)"
                break

        extra_tags = {
            "loop_exit_reason": loop_exit_reason,
            "loop_iterations": loop_iterations,
        }

        usage_metadata = UsageMetadata(
            total_tokens=collector.total_tokens,
            prompt_tokens=collector.total_prompt_tokens,
            completion_tokens=collector.total_completion_tokens,
            extra_tags=extra_tags,
        )

        self._print_timing_report(
            session_id, collector.execution_sequence, logs=collector.logs
        )

        return final_response, collector.logs, usage_metadata, session_id

    def _print_timing_report(
        self,
        session_id: str,
        execution_sequence: list,
        logs: list[TraceLogEvent] = None,
    ):
        print(f"\n--- Tool Execution Path [{session_id}] ---")

        if logs:
            for event in logs:
                timestamp = (
                    event.timestamp.split("T")[1][:12]
                    if event.timestamp and "T" in event.timestamp
                    else event.timestamp
                )

                if event.type == TraceEventType.ADK_EVENT and event.role == "system":
                    print(f"[{timestamp}] {event.author}")

                elif event.type == TraceEventType.TOOL_USE:
                    tool_input_summary = (
                        str(event.tool_input)[:100] + "..."
                        if len(str(event.tool_input)) > 100
                        else str(event.tool_input)
                    )
                    print(f"  -> Tool Call: {event.tool_name}({tool_input_summary})")

                elif event.type == TraceEventType.TOOL_RESULT:
                    tool_output_summary = (
                        str(event.tool_output)[:100] + "..."
                        if len(str(event.tool_output)) > 100
                        else str(event.tool_output)
                    )
                    print(f"  <- Tool Output: {tool_output_summary}")

                elif event.type == TraceEventType.MESSAGE and event.role == "model":
                    content_preview = (
                        event.content[:50].replace("\n", " ") + "..."
                        if len(event.content) > 50
                        else event.content
                    )
                    print(f'  [Model] {event.author}: "{content_preview}"')

        else:
            print("(Detailed logs not available, showing agent sequence)")
            for item in execution_sequence:
                token_str = ""
                if (
                    item.get("prompt_tokens", 0) > 0
                    or item.get("completion_tokens", 0) > 0
                ):
                    token_str = f" [Tokens: {item.get('prompt_tokens', 0)}P + {item.get('completion_tokens', 0)}C]"
                print(f"{item['agent']}: {item['duration']:.2f}s{token_str}")

        print("-------------------------------------------\n")