"""
Experiment 30: Statistical Discovery V10 (Robust Deterministic Retrieval).
"""

from typing import Any, Optional, AsyncGenerator
import os
import shutil
import subprocess
import tempfile
import json
from pathlib import Path

from google.adk.agents import LlmAgent, SequentialAgent, Agent, InvocationContext
from google.adk.events import Event
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from benchmarks.answer_generators.adk_agents import (
    DEFAULT_MODEL_NAME,
    RotatingKeyGemini,
    SetupAgentCodeBased,
    PromptSanitizerAgent,
    CodeBasedRunner,
    CodeBasedFinalVerifier,
    CodeBasedTeardownAgent,
)
from benchmarks.answer_generators.debug_adk_agents import input_guard_callback
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from benchmarks.answer_generators.adk_schemas import RelevantModules

class RobustKnowledgeAgent(Agent):
    """
    Improved Knowledge Agent with robust state parsing.
    """
    def __init__(self, tools_helper: AdkTools, **kwargs):
        super().__init__(**kwargs)
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # 1. Get proposed modules from state (handle object or string)
        proposed_data = ctx.session.state.get("relevant_modules_json")
        modules = []

        if isinstance(proposed_data, str):
            try:
                # Handle possible markdown blocks
                clean_json = proposed_data
                if "```json" in proposed_data:
                    clean_json = proposed_data.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in proposed_data:
                    clean_json = proposed_data.split("```", 1)[1].split("```", 1)[0].strip()
                
                data = json.loads(clean_json)
                modules = data.get("modules", [])
            except:
                modules = []
        elif isinstance(proposed_data, dict):
            modules = proposed_data.get("modules", [])
        elif hasattr(proposed_data, "modules"):
            modules = proposed_data.modules

        # 2. Fetch help for each
        knowledge_parts = []
        successful_fetches = 0
        for m in modules:
            try:
                help_text = await self._tools_helper.get_module_help(m)
                if "Error" not in help_text and "No statistical data" not in help_text:
                    successful_fetches += 1
                knowledge_parts.append(f"--- API Reference for {m} ---\n{help_text}\n")
            except Exception as e:
                knowledge_parts.append(f"--- Error for {m} ---\nModule not found or invalid: {e}\n")

        full_context = "\n".join(knowledge_parts)
        
        # 3. Save to state
        ctx.session.state["knowledge_context"] = full_context
        
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Retrieved context for {successful_fetches}/{len(modules)} modules.")]
            )
        )

def create_debug_structured_adk_agent_v10(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 30: Robust 3-stage pipeline.
    """

    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model = model_name

    setup_agent = SetupAgentCodeBased(
        name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper
    )

    prompt_sanitizer_agent = PromptSanitizerAgent(
        model=model,
        include_contents='none',
        output_key="sanitized_user_request",
    )

    module_proposer = LlmAgent(
        name="module_proposer",
        model=model,
        output_key="relevant_modules_json",
        output_schema=RelevantModules,
        include_contents='none',
        instruction=(
            """Analyze the following request and propose a list of fully qualified Python module paths to inspect.
Request: {sanitized_user_request}

Propose modules likely to contain:
1. The parent class (e.g. `BaseAgent`).
2. Any types seen in signatures (e.g. `Event`, `InvocationContext`).
3. Core library modules (e.g. `google.adk.agents`).

Output ONLY JSON."""
        )
    )

    fetcher_agent = RobustKnowledgeAgent(
        name="knowledge_fetcher",
        tools_helper=tools_helper
    )

    solver_agent = LlmAgent(
        name="solver_agent",
        model=model,
        tools=[], 
        include_contents='none',
        output_key="candidate_response",
        before_agent_callback=input_guard_callback,
        instruction=(
            """You are the Expert Codebase Solver. 
Request: {sanitized_user_request}

**API TRUTH CONTEXT:**
{knowledge_context}

**STRICT PROTOCOL:**
1. **Identify Signatures:** Look at the provided API context. Identify the EXACT method signatures you need to override.
2. **Strict Verification:** If you implement a class inheriting from one in the context, you MUST use the EXACT method names and parameter types shown.
3. **AsyncGenerator Enforcement:** If a method returns `AsyncGenerator`, you MUST use `async def` and `yield`.
4. **Keyword Argument Enforcement:** If a class is a Pydantic model (has `model_fields` in context), you MUST use keyword arguments (e.g. `name=name`).

Output reasoning then code."""
        ),
    )

    code_based_runner = CodeBasedRunner(
        name="code_based_runner",
        tools_helper=tools_helper,
        model_name=model_name
    )

    final_verifier = CodeBasedFinalVerifier(
        name="final_verifier",
        tools_helper=tools_helper
    )

    teardown_agent = CodeBasedTeardownAgent(
        name="teardown_agent", 
        workspace_root=tools_helper.workspace_root, 
        tools_helper=tools_helper
    )

    agent_obj = SequentialAgent(
        name="robust_deterministic_solver",
        sub_agents=[
            setup_agent,
            prompt_sanitizer_agent,
            module_proposer,
            fetcher_agent,
            solver_agent,
            code_based_runner,
            final_verifier,
            teardown_agent,
        ],
    )

    return agent_obj

def create_statistical_v10_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 30 (ADK_STATISTICAL_V10).
    """
    name_prefix="ADK_STATISTICAL_V10"
    folder_prefix="adk_stat_v10_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v10(
        tools_helper=tools_helper, 
        model_name=model_name, 
        api_key_manager=api_key_manager
    )

    async def setup_hook():
        print(f"[{name_prefix}] Setting up workspace at {workspace_root}")
        workspace_root.mkdir(parents=True, exist_ok=True)
        repos_dir = workspace_root / "repos"
        adk_repo_dir = repos_dir / "adk-python"
        repos_dir.mkdir(exist_ok=True)
        if not adk_repo_dir.exists():
            subprocess.run(["git", "clone", "--branch", adk_branch, "https://github.com/google/adk-python.git", str(adk_repo_dir)], check=True, capture_output=True)
        if not venv_path.exists():
            subprocess.run([os.sys.executable, "-m", "venv", str(venv_path)], check=True)
            pip_cmd = [str(venv_path / "bin" / "pip"), "install"]
            subprocess.run(pip_cmd + ["--upgrade", "--quiet", "pip"], check=True)
            subprocess.run(pip_cmd + ["--quiet", "pytest", "PyYAML", "--index-url", "https://pypi.org/simple"], check=True)
            subprocess.run(pip_cmd + ["--quiet", "-e", str(adk_repo_dir), "--index-url", "https://pypi.org/simple"], check=True)

    async def teardown_hook():
        pass

    return AdkAnswerGenerator(
        agent=agent, 
        name=f"{name_prefix}({model_name})", 
        setup_hook=setup_hook, 
        teardown_hook=teardown_hook, 
        api_key_manager=api_key_manager
    )

