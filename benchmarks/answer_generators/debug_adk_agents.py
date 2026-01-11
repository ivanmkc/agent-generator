"""
Debug version of ADK Agents for Experiment 20.
Statistical ReAct Solver.
"""

from typing import Any, Optional, AsyncGenerator
import os
import shutil
import subprocess
import tempfile
import json
from pathlib import Path

from google.adk.agents import LlmAgent, SequentialAgent, Agent, LoopAgent, InvocationContext
from google.adk.events import Event
from google.adk.tools import FunctionTool, exit_loop, ToolContext
from google.genai import types

from benchmarks.answer_generators.adk_agents import (
    DEFAULT_MODEL_NAME,
    RotatingKeyGemini,
    SetupAgentCodeBased,
    PromptSanitizerAgent,
    DocstringFetcherAgent,
    CodeBasedRunner,
    CodeBasedFinalVerifier,
    CodeBasedTeardownAgent,
    _create_index_retrieval_agents,
    can_use_output_schema_with_tools
)
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager

from google.adk.agents.callback_context import CallbackContext

def create_debug_structured_adk_agent(
    tools_helper: AdkTools,
    model_name: str = DEFAULT_MODEL_NAME,
    api_key_manager: ApiKeyManager | None = None,
    retrieval_agents: list[Agent] = [],
    use_loop_history: bool = True,
) -> SequentialAgent:
    """
    Experiment 20: Single-Agent Solver with Statistical Discovery.
    """

    # --- Guard Implementation ---
    def input_guard_callback(callback_context: CallbackContext):
        """Prevents the solver from running if input state is corrupted."""
        # Dynamic context attribute resolution to handle different ADK versions/mocks
        ctx = getattr(callback_context, 'invocation_context', None) or \
              getattr(callback_context, 'context', None) or \
              getattr(callback_context, '_invocation_context', None)
        
        if not ctx:
            raise RuntimeError("CRITICAL: Could not resolve InvocationContext from CallbackContext.")

        sanitized_request = ctx.session.state.get("sanitized_user_request")
        
        if not sanitized_request or sanitized_request == "null":
            # Log heavily so it shows up in trace
            msg = (
                "CRITICAL GUARD FAILURE: 'sanitized_user_request' is missing or null. "
                "This indicates an upstream failure (e.g., PromptSanitizer failed or Quota Limit hit). "
                "Aborting chain to prevent hallucination."
            )
            print(msg) # Print to stdout for log capture
            raise ValueError(msg)

    # Bespoke Tools
    get_help_tool = FunctionTool(tools_helper.get_module_help)
    search_tool = FunctionTool(tools_helper.search_files)
    
    # Standard tools
    write_tool = FunctionTool(tools_helper.write_file)
    replace_tool = FunctionTool(tools_helper.replace_text)
    exit_loop_tool = FunctionTool(exit_loop)
    read_logs_tool = FunctionTool(tools_helper.read_full_execution_logs)

    # Determine Model
    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model = model_name

    # 0. Setup Agent
    setup_agent = SetupAgentCodeBased(
        name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper
    )

    # 0.2 Prompt Sanitizer
    prompt_sanitizer_agent = PromptSanitizerAgent(
        model=model,
        include_contents='none',
        output_key="sanitized_user_request",
    )

    # 1. The Solver (Statistical Discovery)
    solver_agent = LlmAgent(
        name="solver_agent",
        model=model,
        tools=[get_help_tool, search_tool, write_tool, replace_tool],
        include_contents='default',
        output_key="candidate_response",
        before_agent_callback=input_guard_callback, # Attach Guard
        instruction=(
            """You are the Expert Codebase Solver. 
Input Check: If the following request is empty or 'null', stop and ask for clarification.
Request: {sanitized_user_request}

**STRICT PROTOCOL:**
1. **Locate:** You must find the correct import paths for any classes you need.
   - Use `search_files(pattern)` to find where classes (e.g., 'LogicAgent') are defined.
   - Do NOT guess import paths. For example, do not assume `google.adk.agents.logic` exists unless you verify it.
   - **CRITICAL:** If `search_files` returns NO results and `get_module_help` does not list the class, **YOU MUST DEFINE THE CLASS YOURSELF**. Do NOT try to import a class that you cannot find.
2. **Discovery:** Use `get_module_help(module_name)` to inspect APIs once you know the correct module. 
   - **VERIFY PARENTS & TYPES:** If you inherit from a class (e.g. `BaseAgent`), check its `__init__` signature AND its methods (e.g. `_run_async_impl`) using `get_module_help` BEFORE writing code. 
   - **STRICT TYPES & FIELDS:** Observe the types in the signatures (e.g., `InvocationContext`, `AsyncGenerator[Event, None]`). If you use these types, check their fields using `get_module_help(type_name)` before accessing attributes. Do NOT hallucinate your own types (like `Input` or `Output`) or field names (like `.input`) if they are not verified by tools.
   - Do NOT pass arguments (like `model`) if the parent does not accept them, and ensure you override the CORRECT methods with CORRECT signatures.
   - Pay attention to arguments marked as 'REQUIRED' or having high usage percentages (e.g., 'Used 95%').
3. **Implement:** Write the code. 
   - Use the high-frequency verified signatures.

Output reasoning then code."""
        ),
    )

    code_based_runner = CodeBasedRunner(
        name="code_based_runner",
        tools_helper=tools_helper,
        model_name=model_name
    )

    # 3. Final Verifier
    final_verifier = CodeBasedFinalVerifier(
        name="final_verifier",
        tools_helper=tools_helper
    )

    # 4. Teardown Agent
    teardown_agent = CodeBasedTeardownAgent(
        name="teardown_agent", 
        workspace_root=tools_helper.workspace_root, 
        tools_helper=tools_helper
    )

    agent_obj = SequentialAgent(
        name="debug_single_solver",
        sub_agents=[
            setup_agent,
            prompt_sanitizer_agent,
            solver_agent,
            code_based_runner,
            final_verifier,
            teardown_agent,
        ],
    )

    return agent_obj

def create_react_workflow_adk_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
    use_loop_history: bool = False,
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 20.
    """
    name_prefix="ADK_STATISTICAL"
    folder_prefix="adk_stat_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model = model_name
    agent = create_debug_structured_adk_agent(
        tools_helper=tools_helper, model_name=model_name, api_key_manager=api_key_manager, retrieval_agents=[], use_loop_history=False,
    )
    async def setup_hook():
        print(f"[{name_prefix}] Setting up workspace at {workspace_root}")
        workspace_root.mkdir(parents=True, exist_ok=True)
        repos_dir = workspace_root / "repos"
        adk_repo_dir = repos_dir / "adk-python"
        repos_dir.mkdir(exist_ok=True)
        if not adk_repo_dir.exists():
            print(f"[{name_prefix}] Cloning adk-python...")
            subprocess.run(["git", "clone", "--branch", adk_branch, "https://github.com/google/adk-python.git", str(adk_repo_dir)], check=True, capture_output=True, timeout=300)
        if not venv_path.exists():
            print(f"[{name_prefix}] Creating venv...")
            subprocess.run([os.sys.executable, "-m", "venv", str(venv_path)], check=True, timeout=300)
            pip_cmd = [str(venv_path / "bin" / "pip"), "install"]
            subprocess.run(pip_cmd + ["--upgrade", "--quiet", "pip"], check=True, timeout=300)
            subprocess.run(pip_cmd + ["--quiet", "pytest", "PyYAML", "--index-url", "https://pypi.org/simple"], check=True, timeout=300)
            subprocess.run(pip_cmd + ["--quiet", "-e", str(adk_repo_dir), "--index-url", "https://pypi.org/simple"], check=True, timeout=300)
        print(f"[{name_prefix}] Setup complete.")
    async def teardown_hook():
        pass
    return AdkAnswerGenerator(agent=agent, name=f"{name_prefix}({model_name})", setup_hook=setup_hook, teardown_hook=teardown_hook, api_key_manager=api_key_manager)
