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
            
            # 2. Read 'final_answer.json' from workspace
            answer_file = self.workspace_root / "final_answer.json"
            if answer_file.exists():
                with open(answer_file, "r", encoding="utf-8") as f:
                    json_str = f.read()
            else:
                # Fallback to response_text
                if "```json" in response_text:
                    json_str = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                else:
                    json_str = response_text.strip()

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

class RefinedKnowledgeSolver(LlmAgent):
    """
    V42: Refined solver with explicit file tree awareness and strict reasoning guidelines.
    """
    def __init__(self, model, tools_helper: AdkTools, **kwargs):
        
        # Define Tools
        async def get_file_tree(dir_path: str = ".", tool_context: ToolContext = None) -> str:
            """Lists files and directories to understand project structure."""
            return tools_helper.list_directory(dir_path)

        async def search_files(query: str, tool_context: ToolContext) -> str:
            """Searches for files containing the query string."""
            return await tools_helper.search_files(query, path=".")

        async def get_module_help(module_name: str, tool_context: ToolContext) -> str:
            """Gets the docstring and API signature for a Python module."""
            return await tools_helper.get_module_help(module_name)
            
        async def read_file(file_path: str, tool_context: ToolContext) -> str:
            """Reads the content of a specific file."""
            return tools_helper.read_file(file_path)

        async def found_answer(summary: str, tool_context: ToolContext) -> str:
            """Call this when you have found the answer to the user's request."""
            exit_loop(tool_context)
            return f"RESEARCH SUMMARY:\n{summary}"

        super().__init__(
            name="refined_knowledge_solver",
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
Find the EXACT answer in the codebase. Do not guess. Do not hallucinate.

**REASONING GUIDELINES (CRITICAL):**
1. **Map First:** Use `get_file_tree` to see the project structure. Do not search blindly if you don't know where the source code lives (hint: look in `src/google/adk`).
2. **Public API Bias:** If you find an internal class (e.g., `adk.impl.Foo`), ALWAYS search for where it is exported in the public API (e.g., `google.adk.Foo`). We want the public path.
3. **Evidence Required:** When you find the answer, you MUST quote the exact line of code, docstring parameter, or signature in your internal thought process before calling `found_answer`.
4. **Context Check:** If `get_module_help` returns text, read it carefully. If it returns "Empty" or "Not Found", STOP and use `search_files` or `get_file_tree` to locate the correct module name.

**PROTOCOL:**
1. Call `get_file_tree` to orient yourself.
2. Use `search_files` for unique keywords from the request.
3. Use `get_module_help` or `read_file` to verify the API signature.
4. Call `found_answer` ONLY when you have concrete evidence from the tool outputs.

**FAILURE MODES TO AVOID:**
- **Ignored Context:** Do not ignore the output of `get_module_help`. If it lists parameters, read them.
- **Hallucination:** Do not invent parameters (like `json_mode`) that do not appear in the tool output.
"""
            ),
            **kwargs
        )

class AnswerFormatter(LlmAgent):
    def __init__(self, model, tools_helper: AdkTools, **kwargs):
        
        async def write_answer_file(json_content: str, tool_context: ToolContext) -> str:
            """Writes the final JSON answer to 'final_answer.json'."""
            return tools_helper.write_file("final_answer.json", json_content)

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
1. Generate the JSON object.
2. Call the `write_answer_file` tool with the JSON string.
3. **IMPORTANT:** For `fully_qualified_class_name`, ALWAYS prefer the public path starting with `google.adk`. Do NOT use internal paths (like `_manager` or `impl`).
"""
            ),
            **kwargs
        )

# --- Factory ---

def create_refined_knowledge_generator_v42(
    model_name: str, 
    api_key_manager: ApiKeyManager = None, 
    adk_branch='v1.20.0'
) -> AdkAnswerGenerator:
    
    name_prefix = 'ADK_KNOWLEDGE_V42_REFINED'
    workspace_root = Path(tempfile.mkdtemp(prefix='adk_v42_'))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root/'venv')
    
    if api_key_manager:
        model_flash = RotatingKeyGemini(model='gemini-2.5-flash', api_key_manager=api_key_manager)
    else:
        model_flash = 'gemini-2.5-flash'

    setup_agent = SetupAgentCodeBased(name='setup_agent', workspace_root=workspace_root, tools_helper=tools_helper)
    sanitizer = PromptSanitizerAgent(model=model_flash, include_contents='none', output_key='sanitized_user_request')
    
    # 3. Refined Solver Loop (Flash)
    solver = RefinedKnowledgeSolver(model=model_flash, tools_helper=tools_helper)
    loop = LoopAgent(name="research_loop", sub_agents=[solver], max_iterations=8) # Increased iterations slightly for exploration
    
    trigger = TriggerAgent()
    formatter = AnswerFormatter(model=model_flash, tools_helper=tools_helper)
    
    teardown = CodeBasedTeardownAgent(name='teardown', workspace_root=workspace_root, tools_helper=tools_helper)

    agent = SequentialAgent(
        name='adk_v42',
        sub_agents=[setup_agent, sanitizer, loop, trigger, formatter, teardown]
    )

    return FileBasedAdkAnswerGenerator(
        workspace_root=workspace_root,
        agent=agent, 
        name=f'{name_prefix}(Loop)', 
        setup_hook=setup_hook, 
        api_key_manager=api_key_manager, 
        model_name='gemini-2.5-flash'
    )
