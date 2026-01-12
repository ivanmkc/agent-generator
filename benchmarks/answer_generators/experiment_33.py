"""
Experiment 33: Statistical Discovery V13 (Smart Retrieval).
"""

from typing import Any, Optional, AsyncGenerator
import os
import shutil
import subprocess
import tempfile
import json
import importlib
import inspect
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

class SmartKnowledgeAgent(Agent):
    """
    Knowledge Agent that can resolve both modules and specific classes.
    """
    def __init__(self, tools_helper: AdkTools, **kwargs):
        super().__init__(**kwargs)
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        proposed_data = ctx.session.state.get("relevant_modules_json")
        modules = []

        if isinstance(proposed_data, str):
            try:
                data = json.loads(proposed_data)
                modules = data.get("modules", [])
            except: pass
        elif isinstance(proposed_data, dict):
            modules = proposed_data.get("modules", [])
        elif hasattr(proposed_data, "modules"):
            modules = proposed_data.modules

        # Basic cleanup: if it looks like a class path, keep the parent part too
        expanded_targets = set(modules)
        for m in modules:
            if "." in m:
                parts = m.split(".")
                parent = ".".join(parts[:-1])
                expanded_targets.add(parent)
        
        # Ensure core is always checked
        expanded_targets.add("google.adk.agents")
        expanded_targets.add("google.adk.events")

        knowledge_parts = []
        found_symbols = []
        failed_targets = []

        for target in sorted(list(expanded_targets)):
            try:
                # Try module help first (statistical or runtime)
                help_text = await self._tools_helper.get_module_help(target, depth=0)
                
                if "No statistical data" in help_text and "Module:" not in help_text:
                    failed_targets.append(target)
                else:
                    knowledge_parts.append(f"--- API Reference: {target} ---\n{help_text}\n")
                    found_symbols.append(target)
            except Exception as e:
                failed_targets.append(f"{target} ({e})")

        full_context = "\n".join(knowledge_parts)
        ctx.session.state["knowledge_context"] = full_context
        
        summary = f"FOUND: {', '.join(found_symbols[:5])}..."
        if failed_targets:
            summary += f" | FAILED: {', '.join([str(t) for t in failed_targets[:3]])}..."

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=summary)]
            )
        )

def create_debug_structured_adk_agent_v13(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 33: Robust retrieval with SmartKnowledgeAgent.
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
            """Propose fully qualified Python module paths to inspect for solving the request.
Request: {sanitized_user_request}

**Target Modules:**
- The parent class module (e.g. `google.adk.agents`).
- Any custom agent modules.
- Context and Event modules.

Output ONLY JSON."""
        )
    )

    fetcher_agent = SmartKnowledgeAgent(
        name="smart_fetcher",
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

**STRICT IMPLEMENTATION RULES:**
1. **Source of Truth:** You MUST use the provided context above as the ONLY source for API signatures and fields.
2. **Field Check:** Look for 'Required' and 'Optional' fields in the context. 
   - **Constraint:** If a field (like `instruction` or `model`) is NOT listed for a class, you are FORBIDDEN from passing it to that class's constructor.
3. **Missing Classes:** If a required class (like `LogicAgent`) is FAILED or missing from the context, define it yourself locally.
4. **Keyword Only:** Initialize all Pydantic models with keyword arguments.

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
        name="smart_retrieval_solver",
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

def create_statistical_v13_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 33 (ADK_STATISTICAL_V13).
    """
    name_prefix="ADK_STATISTICAL_V13"
    folder_prefix="adk_stat_v13_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v13(
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

