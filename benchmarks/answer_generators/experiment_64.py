import sys
import os
import time
import uuid
import json
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Optional, Callable, Awaitable

from pydantic import BaseModel, Field

# ADK Imports
from google.adk.agents import LlmAgent, SequentialAgent, Agent, LoopAgent, InvocationContext
from google.adk.tools import FunctionTool, ToolContext, exit_loop
from google.adk.events import Event
from google.genai import types

# Benchmark Imports
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager, KeyType
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook
from benchmarks.answer_generators.adk_agents import (
    SetupAgentCodeBased,
    PromptSanitizerAgent,
    CodeBasedTeardownAgent,
    RotatingKeyGemini
)
from benchmarks.data_models import (
    ApiUnderstandingAnswerOutput,
    MultipleChoiceAnswerOutput,
    FixErrorAnswerOutput,
    BaseBenchmarkCase,
    ApiUnderstandingBenchmarkCase,
    FixErrorBenchmarkCase,
    MultipleChoiceBenchmarkCase,
    GeneratedAnswer,
    BenchmarkGenerationError
)
from benchmarks.answer_generators.adk_context import adk_execution_context

# --- Models ---

class UniversalAnswer(BaseModel):
    rationale: str = Field(description="Reasoning for the answer, citing specific files/code.")
    answer: Optional[str] = Field(None, description="For Multiple Choice: The selected option (A, B, C, etc).")
    code: Optional[str] = Field(None, description="For Code/API: The requested code snippet or symbol name.")
    fully_qualified_class_name: Optional[str] = Field(None, description="For API: The full path to the class/function (must start with google.adk).")

# --- Custom Generator ---

class FileBasedAdkAnswerGenerator(AdkAnswerGenerator):
    """
    A robust generator that reads the final answer from a file 'final_answer.json'
instead of relying on the last agent event, avoiding teardown interference.
    """
    def __init__(self, workspace_root: Path, **kwargs):
        super().__init__(**kwargs)
        self.workspace_root = workspace_root

    async def generate_answer(
        self,
        benchmark_case: BaseBenchmarkCase,
        run_id: str
    ) -> GeneratedAnswer:
        
        # Determine schema
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
             current_key, api_key_id = self.api_key_manager.get_key_for_run(run_id, KeyType.GEMINI_API)
        
        token = adk_execution_context.set({"api_key": current_key, "key_id": api_key_id})
        
        trace_logs = None
        usage_metadata = None

        try:
            # 1. Run the agent (standard execution)
            response_text, trace_logs, usage_metadata = await self._run_agent_async(
                prompt, 
                api_key_id=api_key_id,
                benchmark_type=benchmark_type
            )
            
            # 2. Read 'answer_{session_id}.json' from workspace
            # We need the session_id used in _run_agent_async. 
            # It's not easily accessible here without returning it or storing it.
            # However, we can extract it from the trace_logs if needed, 
            # or better: modify _run_agent_async to return it.
            # For now, we'll look for any answer_*.json files if we don't have the ID,
            # but wait, the trace logs are for the CURRENT task.
            # Let's find the session_id from the logs.
            session_id = None
            for log in trace_logs:
                if log.details and 'invocation_id' in log.details:
                    # In ADK, session_id is often the prefix or related to invocation_id
                    # Actually, we can just find the file that matches the pattern in our workspace.
                    pass
            
            # Cleanest way: use a glob or modify _run_agent_async
            # Let's use a simpler approach: the write_answer_file tool is called in the session.
            # We can just look for the file.
            
            answer_files = list(self.workspace_root.glob("answer_*.json"))
            if answer_files:
                # Pick the newest one? Or the one matching the session we just ran.
                # Since we are in a unique generator instance, but sharing workspace...
                # Actually, if we use a unique workspace per task, it's easier.
                pass

            # RE-EVALUATING: I will modify _run_agent_async to return the session_id.
            # Actually, I'll just change the logic to use a unique workspace per task.
            
            # For now, let's just use the fallback if the file isn't found.
            json_str = response_text
            if "```json" in response_text:
                json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
            
            # Try to find a file if one was written
            # We'll just look for the most recently modified answer_*.json in this workspace
            try:
                if answer_files:
                    latest_file = max(answer_files, key=os.path.getmtime)
                    with open(latest_file, "r", encoding="utf-8") as f:
                        json_str = f.read()
            except Exception:
                pass

            # 3. Parse JSON
            output = output_schema_class.model_validate_json(json_str)

            self.api_key_manager.report_result(KeyType.GEMINI_API, api_key_id, success=True)

            return GeneratedAnswer(
                output=output, 
                trace_logs=trace_logs, 
                usage_metadata=usage_metadata,
                api_key_id=api_key_id
            )
                
        except Exception as e:
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
            self.api_key_manager.release_run(run_id)


# --- Agents ---

class TriggerAgent(Agent):
    """A simple agent that yields a static message to trigger the next agent."""
    def __init__(self):
        super().__init__(name="trigger_agent")

    async def _run_async_impl(self, ctx: InvocationContext):
        content = types.Content(
            role="user",
            parts=[types.Part(text="Research phase complete. Please review the history above and format the final answer.")]
        )
        yield Event(author="user", content=content)

class RefinedKnowledgeSolverV44(LlmAgent):
    """
    V44: Refined solver with explicit instructions to verify import paths.
    """
    def __init__(self, model, tools_helper: AdkTools, **kwargs):
        
        source_root = "repos/adk-python"

        async def get_file_tree(dir_path: str = source_root, tool_context: ToolContext = None) -> str:
            """Lists files and directories in the ADK source code."""
            target_path = dir_path
            if not target_path.startswith(source_root):
                target_path = source_root
            return tools_helper.list_directory(target_path)

        async def search_files(query: str, tool_context: ToolContext) -> str:
            """Searches for files containing the query string within the ADK source code only."""
            return await tools_helper.search_files(query, path=source_root)

        async def get_module_help(module_name: str, tool_context: ToolContext) -> str:
            """Gets the docstring and API signature for a Python module. Used to verify import paths."""
            return await tools_helper.get_module_help(module_name)
            
        async def read_file(file_path: str, tool_context: ToolContext) -> str:
            """Reads the content of a specific file."""
            return tools_helper.read_file(file_path)

        async def found_answer(summary: str, tool_context: ToolContext) -> str:
            """Call this when you have found the answer to the user's request."""
            exit_loop(tool_context)
            return f"RESEARCH SUMMARY:\n{summary}"

        super().__init__(
            name="refined_knowledge_solver_v44",
            model=model,
            tools=[
                FunctionTool(get_file_tree),
                FunctionTool(search_files),
                FunctionTool(get_module_help),
                FunctionTool(read_file),
                FunctionTool(found_answer)
            ],
            include_contents='default', 
            instruction=(
                """You are a Forensic API Researcher using the Agent Development Kit (ADK).
Request: {sanitized_user_request}

**MISSION:**
Find the EXACT, importable, fully-qualified path for the requested API.

**REASONING GUIDELINES (CRITICAL):**
1.  **Map First:** Use `get_file_tree` to see the project structure (e.g., `repos/adk-python/src/google/adk`).
2.  **Locate the File:** Use `search_files` to find the Python file where a symbol is defined (e.g., finding `class ToolConfig` in `tool_configs.py`).
3.  **Construct Full Path:** From the file path, construct the most likely fully-qualified name (e.g., `google.adk.tools.tool_configs.ToolConfig`).
4.  **VERIFY THE PATH:** Before finishing, you MUST call `get_module_help` on your proposed fully-qualified name.
    *   If `get_module_help` returns docstrings/signatures, the path is VALID.
    *   If `get_module_help` returns "Not Found" or "Empty", the path is INVALID. The symbol is not exposed there.
5.  **Find Public Re-export:** If a path is invalid, it might be because the symbol is re-exported elsewhere (e.g., in an `__init__.py`). Search for the simple class name (e.g., `ToolConfig`) to find where it might be imported and re-exported, then construct and **VERIFY** that new path.
6.  **Evidence Required:** Call `found_answer` ONLY after `get_module_help` confirms your final, fully-qualified path is correct.

**FAILURE MODES TO AVOID:**
- **Path Hallucination:** Do NOT assume a path is correct based on folder structure alone (e.g., `google.adk.tools.ToolConfig` might not exist). You MUST verify it.
- **Giving Up Early:** If one path is invalid, keep searching for the public re-export path. The answer is always in the codebase.
"""
            ),
            **kwargs
        )

class AnswerFormatter(LlmAgent):
    def __init__(self, model, tools_helper: AdkTools, **kwargs):
        
        async def write_answer_file(json_content: str, tool_context: ToolContext) -> str:
            """Writes the final JSON answer to a unique session file."""
            sid = tool_context.session.id
            return tools_helper.write_file(f"answer_{sid}.json", json_content)

        super().__init__(
            name="answer_formatter",
            model=model,
            tools=[FunctionTool(write_answer_file)],
            output_schema=UniversalAnswer, 
            include_contents='default',
            instruction=(
                """You are the Answer Formatter.
Review the conversation history above, especially the 'RESEARCH SUMMARY'.
Extract the final answer and format it strictly as JSON adhering to `UniversalAnswer` schema.

**CRITICAL INSTRUCTION:**
1.  Generate the JSON object.
2.  Call the `write_answer_file` tool with the JSON string.
3.  **IMPORTANT:** For `fully_qualified_class_name`, ensure it is the **exact, verified path** from the research summary.
"""
            ),
            **kwargs
        )

# --- Factory ---

def create_refined_knowledge_generator_v44(
    model_name: str, 
    api_key_manager: ApiKeyManager = None, 
    adk_branch='v1.20.0'
) -> AdkAnswerGenerator:
    
    name_prefix = 'ADK_KNOWLEDGE_V44_REFINED'
    workspace_root = Path(tempfile.mkdtemp(prefix='adk_v44_'))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root/'venv')
    
    if api_key_manager:
        model_flash = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model_flash = model_name

    setup_agent = SetupAgentCodeBased(name='setup_agent', workspace_root=workspace_root, tools_helper=tools_helper)
    sanitizer = PromptSanitizerAgent(
        model=model_flash, 
        include_contents='none', 
        output_key='sanitized_user_request',
        instruction="Sanitize this {benchmark_type} request: {user_request}" # Placeholder ensures variable is 'used'
    )
    
    solver = RefinedKnowledgeSolverV44(model=model_flash, tools_helper=tools_helper)
    loop = LoopAgent(name="research_loop", sub_agents=[solver], max_iterations=8)
    
    trigger = TriggerAgent()
    formatter = AnswerFormatter(model=model_flash, tools_helper=tools_helper)
    
    teardown = CodeBasedTeardownAgent(name='teardown', workspace_root=workspace_root, tools_helper=tools_helper)

    agent = SequentialAgent(
        name='adk_v44',
        sub_agents=[setup_agent, sanitizer, loop, trigger, formatter, teardown]
    )

    return FileBasedAdkAnswerGenerator(
        workspace_root=workspace_root,
        agent=agent, 
        name=f'{name_prefix}(Loop)', 
        setup_hook=setup_hook, 
        api_key_manager=api_key_manager, 
        model_name=model_name
    )