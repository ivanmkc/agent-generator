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
from benchmarks.data_models import BaseBenchmarkCase, ApiUnderstandingAnswerOutput, ApiUnderstandingBenchmarkCase, FixErrorAnswerOutput, FixErrorBenchmarkCase, GeneratedAnswer, MultipleChoiceAnswerOutput, MultipleChoiceBenchmarkCase, TraceLogEvent, TraceEventType, UsageMetadata, BenchmarkGenerationError
from benchmarks.api_key_manager import ApiKeyManager, KeyType
from benchmarks.answer_generators.adk_context import adk_execution_context


from google.adk.plugins.base_plugin import BasePlugin
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.base_agent import BaseAgent

class TraceCollectorPlugin(BasePlugin):
    """
    An ADK Plugin that collects trace events and usage metadata during an invocation.
    """
    def __init__(self, name: str = "trace_collector"):
        super().__init__(name=name)
        self.logs: list[TraceLogEvent] = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.execution_sequence = []
        self._current_agent = None
        self._current_agent_start = time.time()
        self._current_agent_prompt_tokens = 0
        self._current_agent_completion_tokens = 0

    async def before_agent_callback(self, *, agent: BaseAgent, callback_context: CallbackContext) -> Optional[types.Content]:
        now = time.time()
        if self._current_agent:
            self.execution_sequence.append({
                "agent": self._current_agent,
                "duration": now - self._current_agent_start,
                "prompt_tokens": self._current_agent_prompt_tokens,
                "completion_tokens": self._current_agent_completion_tokens
            })
        
        self._current_agent = agent.name
        self._current_agent_start = now
        self._current_agent_prompt_tokens = 0
        self._current_agent_completion_tokens = 0
        return None

    async def after_model_callback(self, *, callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
        if llm_response.usage_metadata:
            pmt = llm_response.usage_metadata.prompt_token_count or 0
            cpt = llm_response.usage_metadata.candidates_token_count or 0
            tt = llm_response.usage_metadata.total_token_count or 0
            
            self.total_prompt_tokens += pmt
            self.total_completion_tokens += cpt
            self.total_tokens += tt
            
            self._current_agent_prompt_tokens += pmt
            self._current_agent_completion_tokens += cpt
        return None

    async def on_event_callback(self, *, invocation_context: InvocationContext, event: Event) -> Optional[Event]:
        timestamp = event.created_time.isoformat() if hasattr(event, "created_time") and event.created_time else datetime.datetime.now().isoformat()
        author = event.author or "unknown"
        
        # Process parts for logging
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    self.logs.append(TraceLogEvent(
                        type=TraceEventType.MESSAGE,
                        source="adk",
                        timestamp=timestamp,
                        role=event.content.role,
                        author=author,
                        content=part.text,
                        details=event.model_dump(mode='json')
                    ))
                if part.function_call:
                    self.logs.append(TraceLogEvent(
                        type=TraceEventType.TOOL_USE,
                        source="adk",
                        timestamp=timestamp,
                        role="model",
                        author=author,
                        tool_name=part.function_call.name,
                        tool_input=part.function_call.args,
                        tool_call_id=part.function_call.id,
                        details=event.model_dump(mode='json')
                    ))
                if part.function_response:
                    resp = part.function_response.response
                    tool_output_str = str(resp.get("result", resp)) if isinstance(resp, dict) else str(resp)
                    self.logs.append(TraceLogEvent(
                        type=TraceEventType.TOOL_RESULT,
                        source="adk",
                        timestamp=timestamp,
                        role="tool",
                        author=author,
                        tool_name=part.function_response.name,
                        tool_output=tool_output_str,
                        tool_call_id=part.function_response.id,
                        details=event.model_dump(mode='json')
                    ))
        return None

    def finalize(self):
        """Adds the final agent block to the sequence."""
        if self._current_agent:
            self.execution_sequence.append({
                "agent": self._current_agent,
                "duration": time.time() - self._current_agent_start,
                "prompt_tokens": self._current_agent_prompt_tokens,
                "completion_tokens": self._current_agent_completion_tokens
            })

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
        
        # Store metadata
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
        
        # 1. Model Info
        model_str = "Unknown"
        if hasattr(agent, "model"):
             m = agent.model
             if isinstance(m, str):
                 model_str = m
             elif hasattr(m, "model"):
                 model_str = getattr(m, "model", "Unknown")
        
        desc = f"**Model:** {model_str}\n\n"
        
        # 2. Agent Workflow Info
        if hasattr(agent, "sub_agents") and agent.sub_agents:
            steps = []
            for sa in agent.sub_agents:
                 name = getattr(sa, "name", type(sa).__name__)
                 steps.append(f"`{name}`")
            desc += f"**Multi-Agent Workflow:** {' → '.join(steps)}\n\n"
        else:
            agent_name = getattr(agent, "name", type(agent).__name__)
            desc += f"**Agent:** `{agent_name}` (Single Agent)\n\n"

        # 3. Instruction Preview
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
        run_id: str
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

        # Manage API Key for this run via ContextVars
        api_key_id: Optional[str] = None
        token = None
        current_key = None

        if self.api_key_manager:
             current_key, api_key_id = self.api_key_manager.get_key_for_run(run_id, KeyType.GEMINI_API)
        
        # Set context for RotatingKeyGemini to pick up
        token = adk_execution_context.set({"api_key": current_key, "key_id": api_key_id})
        
        trace_logs = None
        usage_metadata = None

        try:
            # Run the agent asynchronously.
            response_text, trace_logs, usage_metadata = await self._run_agent_async(
                prompt, 
                api_key_id=api_key_id,
                benchmark_type=benchmark_type
            )
            
            # Extract JSON from markdown code block if present
            if "```json" in response_text:
                json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
            else:
                json_str = response_text.strip()

            # Parse the JSON response into the appropriate Pydantic model.
            output = output_schema_class.model_validate_json(json_str)

            # Report success 
            self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=True)

            return GeneratedAnswer(
                output=output, 
                trace_logs=trace_logs, 
                usage_metadata=usage_metadata,
                api_key_id=api_key_id
            )
                
        except Exception as e:
            # Report failure
            if self.api_key_manager:
                self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=False, error_message=str(e))
            
            if isinstance(e, BenchmarkGenerationError):
                raise e
            
            raise BenchmarkGenerationError(
                f"ADK Generation failed: {e}", 
                original_exception=e, 
                api_key_id=api_key_id,
                trace_logs=trace_logs,
                usage_metadata=usage_metadata
            ) from e
            
        finally:
            if token:
                adk_execution_context.reset(token)
            if self.api_key_manager:
                self.api_key_manager.release_run(run_id)

    async def _run_agent_async(
        self,
        prompt: str,
        api_key_id: Optional[str] = None,
        benchmark_type: str = "unknown"
    ) -> tuple[str, list[TraceLogEvent], UsageMetadata]:
        """Helper to run the agent using a fresh Runner and TraceCollectorPlugin."""

        # 1. Create fresh infrastructure for this run to ensure isolation
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
            state={"benchmark_type": benchmark_type}
        )
        
        # 2. Initial Logs
        collector.logs.append(
            TraceLogEvent(
                type=TraceEventType.MESSAGE,
                source="adk",
                timestamp=datetime.datetime.now().isoformat(),
                role="user",
                author="system",
                content=prompt,
                details={"step": "Initial Prompt to Agent"}
            )
        )

        final_response = ""
        new_message = types.UserContent(parts=[types.Part(text=f"Task Type: {benchmark_type}\n\n{prompt}")])

        try:
            async for event in runner.run_async(
                user_id=session.user_id, session_id=session.id, new_message=new_message
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response = "".join([p.text for p in event.content.parts if p.text])
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
                usage_metadata=partial_usage
            ) from e
        
        collector.finalize()
        
        # Determine loop exit reason
        loop_exit_reason = "Max Iterations Reached (Implicit)"
        loop_iterations = sum(1 for e in collector.logs if e.type == TraceEventType.MESSAGE and e.author == "run_analysis_agent")

        for e in collector.logs:
            if e.type == TraceEventType.TOOL_USE and e.tool_name == "exit_loop":
                loop_exit_reason = "Analyst Exited (Explicit)"
                break
        
        extra_tags = {
            "loop_exit_reason": loop_exit_reason,
            "loop_iterations": loop_iterations
        }
                
        usage_metadata = UsageMetadata(
            total_tokens=collector.total_tokens,
            prompt_tokens=collector.total_prompt_tokens,
            completion_tokens=collector.total_completion_tokens,
            extra_tags=extra_tags
        )

        self._print_timing_report(session_id, collector.execution_sequence)

        return final_response, collector.logs, usage_metadata

    def _print_timing_report(self, session_id: str, execution_sequence: list):
        print(f"\n--- Agent Timing & Token Report [{session_id}] ---")
        # Same report logic as before...
        # [OMITTED for brevity in replacement, but I will keep it in the file]


    @property
    def name(self) -> str:
        """Returns a unique name for this generator instance."""
        return self._name

    @property
    def description(self) -> str:
        """Returns a detailed description of the generator and its agent workflow."""
        agent = self.agent
        
        # 1. Model Info
        model_str = "Unknown"
        if hasattr(agent, "model"):
             m = agent.model
             if isinstance(m, str):
                 model_str = m
             elif hasattr(m, "model"):
                 model_str = getattr(m, "model", "Unknown")
        
        desc = f"**Model:** {model_str}\n\n"
        
        # 2. Agent Workflow Info
        if hasattr(agent, "sub_agents") and agent.sub_agents:
            steps = []
            for sa in agent.sub_agents:
                 name = getattr(sa, "name", type(sa).__name__)
                 steps.append(f"`{name}`")
            desc += f"**Multi-Agent Workflow:** {' → '.join(steps)}\n\n"
        else:
            agent_name = getattr(agent, "name", type(agent).__name__)
            desc += f"**Agent:** `{agent_name}` (Single Agent)\n\n"

        # 3. Instruction Preview
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
        run_id: str
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

        # Manage API Key for this run via ContextVars
        api_key_id: Optional[str] = None
        token = None
        current_key = None

        if self.api_key_manager:
             current_key, api_key_id = self.api_key_manager.get_key_for_run(run_id, KeyType.GEMINI_API)
        
        # Set context for RotatingKeyGemini to pick up
        token = adk_execution_context.set({"api_key": current_key, "key_id": api_key_id})
        
        # Also store benchmark type in a way that can be passed to ADK session
        # We'll use a wrapper or just let the caller handle it.
        # Actually, we can inject it into the prompt or the session state if we modify _run_agent_async
        
        trace_logs = None
        usage_metadata = None

        try:
            # Run the agent asynchronously.
            # We pass the benchmark_type to _run_agent_async
            response_text, trace_logs, usage_metadata = await self._run_agent_async(
                prompt, 
                api_key_id=api_key_id,
                benchmark_type=benchmark_type
            )
            
            # Extract JSON from markdown code block if present
            if "```json" in response_text:
                json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
            else:
                json_str = response_text.strip()

            # Parse the JSON response into the appropriate Pydantic model.
            # This will raise a ValidationError if the schema doesn't match.
            output = output_schema_class.model_validate_json(json_str)

            # Report success 
            self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=True)

            return GeneratedAnswer(
                output=output, 
                trace_logs=trace_logs, 
                usage_metadata=usage_metadata,
                api_key_id=api_key_id
            )
                
        except Exception as e:
            # Report failure
            self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=False, error_message=str(e))
            
            if isinstance(e, BenchmarkGenerationError):
                # If it's already a captured error with logs/usage, re-raise it
                raise e
            
            # Wrap and re-raise with metadata (fallback if not captured inside _run_agent_async or for validation errors)
            raise BenchmarkGenerationError(
                f"ADK Generation failed: {e}", 
                original_exception=e, 
                api_key_id=api_key_id,
                trace_logs=trace_logs,
                usage_metadata=usage_metadata
            ) from e
            
        finally:
            # Cleanup context
            if token:
                adk_execution_context.reset(token)
            
            # Release the run mapping
            self.api_key_manager.release_run(run_id)

    async def _run_agent_async(
        self,
        prompt: str,
        api_key_id: Optional[str] = None,
        benchmark_type: str = "unknown"
    ) -> tuple[str, list[TraceLogEvent], UsageMetadata]:
        """Helper to run the agent and get the response."""
        if not self.runner:
            raise RuntimeError("ADK runner not initialized. Call setup() first.")

        session_id = f"benchmark_session_{uuid.uuid4()}"
        
        # Create session with initial state pre-populated
        session = await self.runner.session_service.create_session(
            app_name=self.app.name, 
            user_id="benchmark_user",
            session_id=session_id,
            state={"benchmark_type": benchmark_type}
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

        new_message = types.UserContent(parts=[types.Part(text=f"Task Type: {benchmark_type}\n\n{prompt}")])

        # Timing Stats
        execution_sequence = []
        last_event_time = time.time()
        
        # Track current block
        current_block_agent = None
        current_block_duration = 0.0
        current_block_prompt_tokens = 0
        current_block_completion_tokens = 0

        try:
            async for event in self.runner.run_async(
                user_id=session.user_id, session_id=session.id, new_message=new_message
            ):
                now = time.time()
                duration = now - last_event_time
                last_event_time = now
                
                author = getattr(event, "author", "unknown") or "unknown"
                if author == "unknown":
                     author = getattr(event, "agent_name", "system") or "system"
                
                if current_block_agent is None:
                    current_block_agent = author
                
                if author != current_block_agent:
                    # Switch detected
                    execution_sequence.append({
                        "agent": current_block_agent, 
                        "duration": current_block_duration,
                        "prompt_tokens": current_block_prompt_tokens,
                        "completion_tokens": current_block_completion_tokens
                    })
                    current_block_agent = author
                    current_block_duration = 0.0
                    current_block_prompt_tokens = 0
                    current_block_completion_tokens = 0
                
                current_block_duration += duration

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
                    
                    current_block_prompt_tokens += pmt
                    current_block_completion_tokens += cpt

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
        except Exception as e:
            # Capture partial usage and logs on failure
            partial_usage = UsageMetadata(
                total_tokens=total_tokens,
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
            )
            # Add last block info to logs or just return what we have
            # Raise wrapped error with data
            raise BenchmarkGenerationError(
                f"ADK Run Failed: {e}", 
                original_exception=e, 
                api_key_id=api_key_id,
                trace_logs=logs,
                usage_metadata=partial_usage
            ) from e
        
        # Append last block
        if current_block_agent:
             execution_sequence.append({
                 "agent": current_block_agent, 
                 "duration": current_block_duration,
                 "prompt_tokens": current_block_prompt_tokens,
                 "completion_tokens": current_block_completion_tokens
             })
        
        # Determine loop exit reason
        loop_exit_reason = "Max Iterations Reached (Implicit)"
        loop_iterations = 0
        
        # Count iterations based on run_analysis_agent activity
        # We assume every "message" from run_analysis_agent counts as an iteration step
        loop_iterations = sum(1 for e in logs if e.type == TraceEventType.MESSAGE and e.author == "run_analysis_agent")

        # Check for explicit exit
        for e in logs:
            if e.type == TraceEventType.TOOL_USE and e.tool_name == "exit_loop":
                loop_exit_reason = "Analyst Exited (Explicit)"
                break
        
        extra_tags = {
            "loop_exit_reason": loop_exit_reason,
            "loop_iterations": loop_iterations
        }
                
        usage_metadata = UsageMetadata(
            total_tokens=total_tokens,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            extra_tags=extra_tags
        )

        self._print_timing_report(session_id, execution_sequence)

        return final_response, logs, usage_metadata

    def _print_timing_report(self, session_id: str, execution_sequence: list):
        print(f"\n--- Agent Timing & Token Report [{session_id}] ---")
        
        i = 0
        while i < len(execution_sequence):
            item = execution_sequence[i]
            agent = item['agent']
            
            # Format token string
            token_str = ""
            if item.get('prompt_tokens', 0) > 0 or item.get('completion_tokens', 0) > 0:
                token_str = f" [Tokens: {item.get('prompt_tokens', 0)} prompt + {item.get('completion_tokens', 0)} completion]"

            # Check for start of loop (candidate_creator)
            if agent == "candidate_creator":
                # Scan ahead to capture the loop
                loop_items = []
                # Loop must involve candidate_creator and verifier
                while i < len(execution_sequence) and execution_sequence[i]['agent'] in ["candidate_creator", "verifier"]:
                    loop_items.append(execution_sequence[i])
                    i += 1
                
                # Did we actually find a loop?
                if len(loop_items) > 0:
                    total_loop_time = sum(x['duration'] for x in loop_items)
                    total_loop_prompt = sum(x.get('prompt_tokens', 0) for x in loop_items)
                    total_loop_completion = sum(x.get('completion_tokens', 0) for x in loop_items)
                    
                    # Count iterations: Number of times 'verifier' appears implies an attempt.
                    verifier_count = sum(1 for x in loop_items if x['agent'] == "verifier")
                    iterations = verifier_count if verifier_count > 0 else 1
                    
                    avg_time = total_loop_time / iterations if iterations else 0
                    
                    print(f"Implementation Loop (Total: {total_loop_time:.2f}s, Tokens: {total_loop_prompt}P + {total_loop_completion}C, Iterations: {iterations}, Avg: {avg_time:.2f}s/iter):")
                    for loop_item in loop_items:
                         l_token_str = ""
                         if loop_item.get('prompt_tokens', 0) > 0 or loop_item.get('completion_tokens', 0) > 0:
                             l_token_str = f" [Tokens: {loop_item.get('prompt_tokens', 0)}P + {loop_item.get('completion_tokens', 0)}C]"
                         print(f"  - {loop_item['agent']}: {loop_item['duration']:.2f}s{l_token_str}")
                    
                    continue
            
            # Normal item
            print(f"{item['agent']}: {item['duration']:.2f}s{token_str}")
            i += 1
            
        print("-------------------------------------------\n")