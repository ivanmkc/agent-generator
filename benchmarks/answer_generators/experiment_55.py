"""
Experiment 55: Statistical Discovery V35 (External Formatting).
Based on V34, but removes the in-agent JSON formatting.
Instead, the agent outputs natural text, and we use a separate Gemini Structured Output call
to format the result into the required JSON schema.
"""

from pathlib import Path
import tempfile
import json
import re
from typing import AsyncGenerator, Optional

from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager, KeyType
from benchmarks.data_models import GeneratedAnswer, BenchmarkGenerationError, FixErrorAnswerOutput, ApiUnderstandingAnswerOutput, MultipleChoiceAnswerOutput, BaseBenchmarkCase, FixErrorBenchmarkCase, ApiUnderstandingBenchmarkCase, MultipleChoiceBenchmarkCase
from benchmarks.answer_generators.adk_context import adk_execution_context

from google.adk.agents import LlmAgent, SequentialAgent, Agent, InvocationContext
from google.adk.events import Event
from google.genai import types, Client
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook
from benchmarks.answer_generators.experiment_49 import create_debug_structured_adk_agent_v29
from benchmarks.answer_generators.experiment_53 import _create_fast_prismatic_retrieval_agents_v33, RoutingDelegatorAgent, ContextExpanderCodeBased
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedTeardownAgent, RotatingKeyGemini, DocstringFetcherAgent
from google.adk.tools import FunctionTool, ToolContext

# --- Helpers ---

def format_adk_index(yaml_content: str) -> str:
    """Formats the ADK index YAML into a concise list: <fqn>: <description>"""
    try:
        import yaml
        data = yaml.safe_load(yaml_content)
        modules = data.get("modules", [])
        lines = []
        for mod in modules:
            path = mod.get("path", "unknown")
            desc = mod.get("description", "No description")
            lines.append(f"{path}: {desc}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error formatting index: {e}\nRaw Content:\n{yaml_content}"

# --- Agents ---

class RuntimeDocstringFetcherAgent(Agent):
    """
    Fetches help for selected modules using runtime inspection to ensure docstrings are included.
    (Replaces DocstringFetcherAgent which relied on stats that lacked docstrings).
    """
    def __init__(self, tools_helper: AdkTools, **kwargs):
        super().__init__(**kwargs)
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # 1. Retrieve selected modules
        # Import RelevantModules locally to avoid circular imports if possible, or assume it's in schemas
        from benchmarks.answer_generators.adk_schemas import RelevantModules
        
        relevant_modules_json = ctx.session.state.get("relevant_modules_json", "{}")
        try:
            if isinstance(relevant_modules_json, str):
                if "```json" in relevant_modules_json:
                    relevant_modules_json = relevant_modules_json.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in relevant_modules_json:
                    relevant_modules_json = relevant_modules_json.split("```", 1)[1].split("```", 1)[0].strip()
                relevant_modules = RelevantModules.model_validate_json(relevant_modules_json)
            elif isinstance(relevant_modules_json, dict):
                relevant_modules = RelevantModules.model_validate(relevant_modules_json)
            else:
                relevant_modules = relevant_modules_json
        except Exception as e:
            ctx.session.state["knowledge_context"] = f"Error retrieving knowledge context: {e}"
            yield Event(invocation_id=ctx.invocation_id, author=self.name, content=types.Content(role="model", parts=[types.Part(text=f"Error: {e}")]))
            return

        # 2. Fetch runtime help (docstrings included)
        knowledge_context_parts = []
        for module_name in relevant_modules.modules:
            try:
                # Force runtime inspection
                help_text = await self._tools_helper._get_runtime_module_help(module_name)
                knowledge_context_parts.append(f"--- Help for {module_name} ---\n{help_text}\n")
            except Exception as e:
                knowledge_context_parts.append(f"Error fetching help for {module_name}: {e}\n")

        full_context = "\n".join(knowledge_context_parts)
        ctx.session.state["knowledge_context"] = full_context
        
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(role="model", parts=[types.Part(text=f"Fetched runtime docs for {len(relevant_modules.modules)} modules.")])
        )

def _create_retrieval_agents_v35(tools_helper: AdkTools, model) -> list[Agent]:
    """
    Creates the V35 retrieval chain with formatted index and runtime docstrings.
    """
    # Load and format index
    index_path = Path("benchmarks/adk_index.yaml")
    if index_path.exists():
        with open(index_path, "r") as f:
            raw_index = f.read()
            formatted_index = format_adk_index(raw_index)
    else:
        formatted_index = "Error: adk_index.yaml not found."

    def save_relevant_modules(modules: list[str], tool_context: ToolContext) -> str:
        tool_context.session.state["relevant_modules_json"] = json.dumps({"modules": modules})
        return f"Saved seeds: {modules}"

    save_modules_tool = FunctionTool(save_relevant_modules)

    # 1. Seed Selector (LLM)
    seed_selector_agent = LlmAgent(
        name="seed_selector_agent",
        model=model,
        tools=[save_modules_tool],
        include_contents="none",
        instruction=(
            f"You are the Seed Selector. Select the 1-2 most relevant ADK modules for the request from the index below.\n"
            f"Index (Module: Description):\n{formatted_index}\n"
            "Request: {sanitized_user_request}\n"
        ),
    )

    # 2. Context Expander (Code - reused from V33)
    context_expander_agent = ContextExpanderCodeBased(
        name="context_expander_agent",
        tools_helper=tools_helper
    )
    
    # 3. Docstring Fetcher (Runtime)
    docstring_fetcher_agent = RuntimeDocstringFetcherAgent(
        name="docstring_fetcher_agent", tools_helper=tools_helper
    )
    
    return [seed_selector_agent, context_expander_agent, docstring_fetcher_agent]

# We need a new generator class that handles external formatting
class AdkAnswerGeneratorV35(AdkAnswerGenerator):
    """
    V35 Generator that runs the agent to get text, then calls Gemini again to format it.
    """
    def __init__(self, *args, formatter_model: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.formatter_model = formatter_model

    async def generate_answer(
        self,
        benchmark_case: BaseBenchmarkCase,
        run_id: str
    ) -> GeneratedAnswer:
        """Generates an answer using the ADK Agent + External Formatter."""

        # 1. Determine Schema & Prompts
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

        # 2. Manage API Key
        api_key_id: Optional[str] = None
        token = None
        current_key = None

        if self.api_key_manager:
             current_key, api_key_id = self.api_key_manager.get_key_for_run(run_id, KeyType.GEMINI_API)
        
        token = adk_execution_context.set({"api_key": current_key, "key_id": api_key_id})
        
        trace_logs = None
        usage_metadata = None

        try:
            # 3. Run Agent (Produces Text)
            # We assume the agent simply returns the answer in natural language/code
            response_text, trace_logs, usage_metadata, session_id = await self._run_agent_async(
                prompt, 
                api_key_id=api_key_id,
                benchmark_type=benchmark_type
            )
            
            # 4. External Formatting Call (Structured Output)
            # Use a fresh client with the same key
            client = Client(api_key=current_key)
            
            formatting_prompt = (
                f"You are a helpful assistant. Extracts the final answer from the following text and format it strictly according to the schema.\n\n"
                f"--- BEGIN AGENT OUTPUT ---\n{response_text}\n--- END AGENT OUTPUT ---\n"
            )
            
            # Log Formatter Input
            if trace_logs is None:
                trace_logs = []
            
            from benchmarks.data_models import TraceLogEvent, TraceEventType
            import datetime
            now_iso = datetime.datetime.now().isoformat()
            
            trace_logs.append(TraceLogEvent(
                timestamp=now_iso,
                type=TraceEventType.ADK_EVENT,
                source="formatter_input",
                content=formatting_prompt
            ))

            # Use the injected formatter model (no longer hardcoded)
            format_response = client.models.generate_content(
                model=self.formatter_model,
                contents=formatting_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=output_schema_class
                )
            )
            
            # Log Formatter Output
            trace_logs.append(TraceLogEvent(
                timestamp=datetime.datetime.now().isoformat(),
                type=TraceEventType.ADK_EVENT,
                source="formatter_output",
                content=format_response.text
            ))
            
            # Parse output
            if not format_response.parsed:
                 # Fallback: try parsing text
                 try:
                     output = output_schema_class.model_validate_json(format_response.text)
                 except Exception as parse_err:
                     raise ValueError(f"Formatting failed. Model output: {format_response.text}") from parse_err
            else:
                 output = format_response.parsed

            # Report success 
            self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=True)

            return GeneratedAnswer(
                output=output, 
                trace_logs=trace_logs, 
                usage_metadata=usage_metadata,
                api_key_id=api_key_id
            )
                
        except Exception as e:
            if self.api_key_manager:
                self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=False, error_message=str(e))
            
            if isinstance(e, BenchmarkGenerationError):
                raise e
            
            raise BenchmarkGenerationError(
                f"ADK V35 Generation failed: {e}", 
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

class RawExpertResponseFinalizer(Agent):
    """Simply moves final_expert_output to final_response for the generator to pick up."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        output_str = ctx.session.state.get("final_expert_output", "")
        ctx.session.state["final_response"] = output_str
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name, 
            content=types.Content(role="model", parts=[types.Part(text=output_str)])
        )

def create_debug_structured_adk_agent_v35(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 55: V35 - External Formatting.
    Same as V34 but without the finalizer and with 'natural' instructions.
    """
    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model = model_name

    # 1. Experts
    # Use the injected model for Coding Specialist
    # V29 coding agent already outputs natural text + code block, which is fine.
    # Pass model_name string so v29 creates its own wrapper and CodeBasedRunner gets the string.
    coding_agent = create_debug_structured_adk_agent_v29(tools_helper, model_name, api_key_manager)
    
    # Knowledge Specialist: Updated to use formatted index and runtime docstrings
    retrieval_agents = _create_retrieval_agents_v35(tools_helper, model)
    
    # Instruction for QA Solver
    qa_instr = (
        "You are the ADK Knowledge Expert.\n"
        "Request: {sanitized_user_request}\n"
        "TASK TYPE: {benchmark_type}\n"
        "CONTEXT:\n"
        "{knowledge_context}\n\n"
        "GOAL: Answer the question accurately based on the context.\n"
        "- For Multiple Choice: Explicitly state the correct option letter (e.g., 'Answer: A') and explain why.\n"
        "- For API Questions: Provide the code snippet and the rationale.\n"
        "- For Fix Errors: Provide the corrected code.\n\n"
        "Do NOT try to output JSON. Just give the answer clearly."
    )

    qa_solver = LlmAgent(
        name="qa_solver",
        model=model,
        include_contents='none',
        instruction=qa_instr,
        generate_content_config=types.GenerateContentConfig(
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode='NONE'
                )
            )
        )
    )
    knowledge_agent = SequentialAgent(name="knowledge_specialist", sub_agents=[*retrieval_agents, qa_solver])

    # 2. Delegator
    delegator_agent = RoutingDelegatorAgent(
        name="delegator_agent",
        model=model,
        coding_agent=coding_agent,
        knowledge_agent=knowledge_agent
    )

    # 3. Root Pipeline
    setup_agent = SetupAgentCodeBased(name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)
    
    sanitizer_instruction = (
        "You are a prompt sanitization expert.\n"
        "Original Request: {user_request}\n\n"
        "Task: Extract the core ADK question/task into the following template:\n\n"
        "Question: <user question>\n"
        "Examples: <1 - 2 exemplary examples if applicable, else None>\n"
        "Answer format: <answer format and required parameters and 1 example>\n\n"
        "Remove explicit tool-calling instructions."
    )
    
    prompt_sanitizer_agent = PromptSanitizerAgent(
        model=model, 
        include_contents='none', 
        output_key="sanitized_user_request",
        instruction=sanitizer_instruction
    )
    
    finalizer = RawExpertResponseFinalizer(name="finalizer")
    
    teardown_agent = CodeBasedTeardownAgent(name="teardown_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)

    return SequentialAgent(
        name="adk_statistical_v35",
        sub_agents=[setup_agent, prompt_sanitizer_agent, delegator_agent, finalizer, teardown_agent],
    )

def create_statistical_v35_generator(
    model_name: str,
    formatter_model: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """Factory for Experiment 55."""
    name_prefix="ADK_STATISTICAL_V35"
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_stat_v35_"))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root/"venv")
    
    # Use the passed model_name
    agent = create_debug_structured_adk_agent_v35(tools_helper, model_name, api_key_manager)
    
    # Use our specialized generator class
    return AdkAnswerGeneratorV35(
        agent=agent, 
        name=f"{name_prefix}({model_name})", 
        setup_hook=setup_hook, 
        api_key_manager=api_key_manager, 
        model_name=model_name,
        formatter_model=formatter_model
    )

# --- Legacy Symbols for Compatibility with V36 ---

class LoggedDocstringFetcherAgent(DocstringFetcherAgent):
    """A DocstringFetcherAgent that logs its actions (Placeholder for V36 compatibility)."""
    pass

class VerificationPlanParser(LlmAgent):
    """Parses the verification plan (Placeholder for V36 compatibility)."""
    def __init__(self, name: str = "plan_parser"):
        super().__init__(name=name, model="gemini-2.5-flash", instruction="Parse plan") 

class SmartRunAnalyst(LlmAgent):
    """Analyzes run results (Placeholder for V36 compatibility)."""
    def __init__(self, model, **kwargs):
        super().__init__(name="run_analyst", model=model, instruction="Analyze run", **kwargs)

def _create_logged_retrieval_agents(tools_helper, model):
    """Creates logged retrieval agents (Alias for V33 retrieval for compatibility)."""
    return _create_fast_prismatic_retrieval_agents_v33(tools_helper, model)
