"""
Experiment 32: Statistical Discovery V12 (Context-Aware Retrieval).
"""

from typing import Any, Optional, AsyncGenerator
import os
import shutil
import subprocess
import tempfile
import json
import sys
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

class ContextAwareKnowledgeAgent(Agent):
    """
    Knowledge Agent that ensures PYTHONPATH is set for runtime fallback.
    """
    def __init__(self, tools_helper: AdkTools, **kwargs):
        super().__init__(**kwargs)
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # 1. Get proposed modules
        proposed_data = ctx.session.state.get("relevant_modules_json")
        modules = []

        if isinstance(proposed_data, str):
            try:
                clean_json = proposed_data
                if "```json" in proposed_data:
                    clean_json = proposed_data.split("```json", 1)[1].split("```", 1)[0].strip()
                data = json.loads(clean_json)
                modules = data.get("modules", [])
            except: pass
        elif isinstance(proposed_data, dict):
            modules = proposed_data.get("modules", [])
        elif hasattr(proposed_data, "modules"):
            modules = proposed_data.modules

        # 2. Setup Environment for get_module_help (Runtime Fallback)
        # The ADK repo is at workspace_root / "repos" / "adk-python" / "src"
        adk_src = self._tools_helper.workspace_root / "repos" / "adk-python" / "src"
        
        # We can pass extra_env to get_module_help if it used run_shell_command internally for fallback
        # Wait, get_module_help uses _get_runtime_module_help which creates a temporary runner.
        # I need to ensure that runner has the correct PYTHONPATH.
        
        # I will temporarily modify the tools_helper's environment if possible, 
        # or just rely on the fact that AdkTools.run_shell_command uses venv_path.
        # If the repo was installed in editable mode in the venv, it should work.

        knowledge_parts = []
        successful_fetches = 0
        
        # Priority: Always check 'google.adk.agents' if not already there
        if "google.adk.agents" not in modules:
            modules.append("google.adk.agents")

        for m in modules:
            try:
                # Add depth=1 to get subclasses
                help_text = await self._tools_helper.get_module_help(m, depth=1)
                
                # Check for empty/error
                if "No statistical data" in help_text and "Module:" not in help_text:
                     # This means even runtime search failed.
                     # Let's try one more depth or a specific submodule guess
                     help_text = f"Warning: Could not find detailed info for {m}. Use standard Python inspect or define it yourself if it's not a core class."
                else:
                    successful_fetches += 1
                
                knowledge_parts.append(f"--- API Reference for {m} ---\n{help_text}\n")
            except Exception as e:
                knowledge_parts.append(f"--- Error for {m} ---\n{e}\n")

        full_context = "\n".join(knowledge_parts)
        ctx.session.state["knowledge_context"] = full_context
        
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Retrieved context for {successful_fetches}/{len(modules)} modules.")]
            )
        )

def create_debug_structured_adk_agent_v12(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 32: pipeline + Strict Context Enforcement.
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
- The base/parent class module (e.g. `google.adk.agents`).
- Any custom agent modules mentioned.
- Context and Event modules.

Output ONLY JSON."""
        )
    )

    fetcher_agent = ContextAwareKnowledgeAgent(
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

**GROUND TRUTH API CONTEXT:**
{knowledge_context}

**STRICT IMPLEMENTATION RULES:**
1. **No Hallucinations:** You are FORBIDDEN from importing any class (e.g. `LogicAgent`, `AgentOutput`) that is not explicitly listed in the API context above. 
2. **Missing Classes:** If you need a class that is NOT in the context, you MUST define it yourself as a subclass of `BaseAgent`.
3. **Signature Adherence:** Use the EXACT method names and parameters from the context.
   - Example: If the context shows `_run_async_impl(self, ctx: InvocationContext)`, do NOT use `call()` or `handle()`.
4. **Keyword Only:** Use `name=name` for all Pydantic initializations.

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
        name="context_aware_solver",
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

def create_statistical_v12_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 32 (ADK_STATISTICAL_V12).
    """
    name_prefix="ADK_STATISTICAL_V12"
    folder_prefix="adk_stat_v12_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v12(
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

