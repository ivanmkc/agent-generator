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
            json_str = response_text
            if "```json" in response_text:
                json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
            
            # Try to find a file if one was written
            try:
                answer_files = list(self.workspace_root.glob("answer_*.json"))
                if answer_files:
                    # We'll just look for the most recently modified answer_*.json in this workspace
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

class TaskAwareSolverV45(LlmAgent):
    """
    V45: Task-Aware solver that adjusts its persona based on the benchmark type.
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
            name="task_aware_solver_v45",
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
                """You are an Expert ADK Developer with specialized modes.
Task Type: {benchmark_type}
Request: {sanitized_user_request}

**MODE SWITCHING LOGIC:**

**IF Task Type == 'api_understanding':**
   - Role: Forensic API Researcher.
   - Goal: Find the EXACT, importable, fully-qualified path for the requested API.
   - Protocol:
     1. `get_file_tree` to see structure.
     2. `search_files` to locate the definition.
     3. `get_module_help` to **VERIFY** the import path. If invalid, check re-exports in `__init__.py`.
     4. Call `found_answer` ONLY when the path is verified.

**IF Task Type == 'fix_error':**
   - Role: Senior Software Engineer.
   - Goal: Fix the bug or implement the feature using ONLY valid ADK APIs.
   - Protocol:
     1. Analyze the request to understand the missing or broken functionality.
     2. Use `search_files` and `get_module_help` to discover the correct classes/methods to use. **Do not guess imports.**
     3. Write the COMPLETE fixed code block in the summary.
     4. Call `found_answer` with the fixed code.

**IF Task Type == 'multiple_choice':**
   - Role: Exam Taker.
   - Goal: Select the correct option based on evidence from the codebase.
   - Protocol:
     1. Identify keywords in the question.
     2. Use `search_files` to find relevant code (e.g. `Runner` init, `LlmAgent` params).
     3. Read the implementation details to confirm/deny options.
     4. Call `found_answer` with the selected option and reasoning.

**UNIVERSAL RULES:**
- **Zero Hallucination:** Verify every import path and argument name using tools.
- **Evidence Based:** Your summary must cite the file path where you found the answer.
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
3.  **IMPORTANT:**
    *   For `api_understanding`: Ensure `fully_qualified_class_name` is the verified path.
    *   For `fix_error`: Ensure `code` contains the complete python file content.
    *   For `multiple_choice`: Ensure `answer` is just the letter (A, B, C, D, or E).
"""
            ),
            **kwargs
        )

# --- Factory ---

def create_task_aware_generator_v45(
    model_name: str, 
    api_key_manager: ApiKeyManager = None, 
    adk_branch='v1.20.0'
) -> AdkAnswerGenerator:
    
    name_prefix = 'ADK_TASK_AWARE_V45'
    workspace_root = Path(tempfile.mkdtemp(prefix='adk_v45_'))
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
    
    solver = TaskAwareSolverV45(model=model_flash, tools_helper=tools_helper)
    loop = LoopAgent(name="research_loop", sub_agents=[solver], max_iterations=8)
    
    trigger = TriggerAgent()
    formatter = AnswerFormatter(model=model_flash, tools_helper=tools_helper)
    
    teardown = CodeBasedTeardownAgent(name='teardown', workspace_root=workspace_root, tools_helper=tools_helper)

    agent = SequentialAgent(
        name='adk_v45',
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

