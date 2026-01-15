import sys
import os
from pathlib import Path
import tempfile
import json
from typing import AsyncGenerator, Optional

from pydantic import BaseModel, Field

# ADK Imports
from google.adk.agents import LlmAgent, SequentialAgent, Agent, LoopAgent, InvocationContext
from google.adk.tools import FunctionTool, ToolContext, exit_loop
from google.adk.events import Event
from google.genai import types

# Benchmark Imports
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook
from benchmarks.answer_generators.adk_agents import (
    SetupAgentCodeBased, 
    PromptSanitizerAgent, 
    CodeBasedTeardownAgent, 
    RotatingKeyGemini
)
from benchmarks.data_models import ApiUnderstandingAnswerOutput, MultipleChoiceAnswerOutput, FixErrorAnswerOutput

# --- Models ---

class UniversalAnswer(BaseModel):
    rationale: str = Field(description="Reasoning for the answer, citing specific files/code.")
    answer: Optional[str] = Field(None, description="For Multiple Choice: The selected option (A, B, C, etc).")
    code: Optional[str] = Field(None, description="For Code/API: The requested code snippet or symbol name.")
    fully_qualified_class_name: Optional[str] = Field(None, description="For API: The full path to the class/function.")

# --- Agents ---

class TriggerAgent(Agent):
    """A simple agent that yields a static message to trigger the next agent."""
    def __init__(self):
        super().__init__(name="trigger_agent")

    async def _run_async_impl(self, ctx: InvocationContext):
        # Create a Gemini-compatible Content object
        # We simulate a 'user' message so the next LlmAgent treats it as a new prompt
        content = types.Content(
            role="user",
            parts=[types.Part(text="Research phase complete. Please review the history above and format the final answer.")]
        )
        yield Event(author="user", content=content)

class ReactiveKnowledgeSolver(LlmAgent):
    """
    A reactive agent that uses tools to explore the codebase before answering.
    """
    def __init__(self, model, tools_helper: AdkTools, **kwargs):
        
        # Define Tools
        async def search_files_tool(query: str, tool_context: ToolContext) -> str:
            """Searches for files containing the query string."""
            return await tools_helper.search_files(query, path=".")

        async def get_module_help_tool(module_name: str, tool_context: ToolContext) -> str:
            """Gets the docstring and API signature for a Python module."""
            return await tools_helper.get_module_help(module_name)
            
        async def read_file_tool(file_path: str, tool_context: ToolContext) -> str:
            """Reads the content of a specific file."""
            return tools_helper.read_file(file_path)

        async def found_answer_tool(summary: str, tool_context: ToolContext) -> str:
            """Call this when you have found the answer to the user's request."""
            exit_loop(tool_context)
            return f"RESEARCH SUMMARY:\n{summary}"

        super().__init__(
            name="reactive_knowledge_solver",
            model=model,
            tools=[
                FunctionTool(search_files_tool),
                FunctionTool(get_module_help_tool),
                FunctionTool(read_file_tool),
                FunctionTool(found_answer_tool)
            ],
            include_contents='default', 
            instruction=(
                """You are a Forensic API Researcher using the Agent Development Kit (ADK).
Request: {sanitized_user_request}

**MISSION:**
Find the EXACT answer in the codebase. Do not guess. Do not hallucinate.

**PROTOCOL:**
1. **Search First:** Use `search_files` to find relevant classes or methods. 
   - *Tip:* Search for unique keywords from the request (e.g. "persistence", "plugins", "RunConfig").
2. **Inspect:** Use `get_module_help` or `read_file` to verify the API signature.
3. **Verify:** Does the text EXPLICITLY answer the question?
   - If YES: Call `found_answer_tool` with a detailed summary.
   - If NO: Search again with different terms.

**CRITICAL RULES:**
- If `get_module_help` returns "Empty" or "Not Found", you MUST use `search_files` immediately.
- Never answer based on your internal training data if it contradicts the tools.
"""
            ),
            **kwargs
        )

class AnswerFormatter(LlmAgent):
    """
    Formats the final answer from the solver's context into the required schema.
    """
    def __init__(self, model, **kwargs):
        super().__init__(
            name="answer_formatter",
            model=model,
            tools=[], 
            output_schema=UniversalAnswer, 
            include_contents='default',
            instruction=(
                """You are the Answer Formatter.
Review the conversation history above, especially the 'RESEARCH SUMMARY'.
Extract the final answer and format it strictly.

**GOAL:**
- Fill the `UniversalAnswer` schema.
- For Multiple Choice: set `answer` and `rationale`.
- For API/Code: set `code`, `fully_qualified_class_name`, and `rationale`.

**RULES:**
- Use the evidence found by the 'reactive_knowledge_solver'.
- If the solver failed to find the answer, admit it in the rationale but make your best guess.
"""
            ),
            **kwargs
        )

# --- Factory ---

def create_reactive_knowledge_generator_v39(
    model_name: str, 
    api_key_manager: ApiKeyManager = None, 
    adk_branch='v1.20.0'
) -> AdkAnswerGenerator:
    
    name_prefix = 'ADK_KNOWLEDGE_V39_REACTIVE'
    workspace_root = Path(tempfile.mkdtemp(prefix='adk_v39_'))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root/'venv')
    
    # Models
    if api_key_manager:
        model_flash = RotatingKeyGemini(model='gemini-2.5-flash', api_key_manager=api_key_manager)
        model_pro = RotatingKeyGemini(model='gemini-2.5-pro', api_key_manager=api_key_manager)
    else:
        model_flash = 'gemini-2.5-flash'
        model_pro = 'gemini-2.5-pro'

    # 1. Setup
    setup_agent = SetupAgentCodeBased(name='setup_agent', workspace_root=workspace_root, tools_helper=tools_helper)
    
    # 2. Sanitize
    sanitizer = PromptSanitizerAgent(model=model_flash, include_contents='none', output_key='sanitized_user_request')
    
    # 3. Reactive Loop
    solver = ReactiveKnowledgeSolver(model=model_pro, tools_helper=tools_helper)
    loop = LoopAgent(name="research_loop", sub_agents=[solver], max_iterations=6)
    
    # 4. Trigger (Ensures formatter runs)
    trigger = TriggerAgent()

    # 5. Formatter
    formatter = AnswerFormatter(model=model_flash)
    
    # 6. Teardown
    teardown = CodeBasedTeardownAgent(name='teardown', workspace_root=workspace_root, tools_helper=tools_helper)

    agent = SequentialAgent(
        name='adk_v39',
        sub_agents=[setup_agent, sanitizer, loop, trigger, formatter, teardown]
    )

    return AdkAnswerGenerator(
        agent=agent, 
        name=f'{name_prefix}(Loop)', 
        setup_hook=setup_hook, 
        api_key_manager=api_key_manager, 
        model_name='mixed'
    )
