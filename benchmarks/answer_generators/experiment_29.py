"""
Experiment 29: Statistical Discovery V9 (Deterministic Retrieval).
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

class DeterministicKnowledgeAgent(Agent):
    """
    A code-based agent that deterministically fetches help for proposed modules.
    Exclusively uses get_module_help.
    """
    def __init__(self, tools_helper: AdkTools, **kwargs):
        super().__init__(**kwargs)
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # 1. Get proposed modules from state
        proposed_modules_json = ctx.session.state.get("relevant_modules_json")
        if not proposed_modules_json:
             yield Event(invocation_id=ctx.invocation_id, author=self.name, content=types.Content(role="model", parts=[types.Part(text="No modules proposed.")]))
             return

        try:
            data = json.loads(proposed_modules_json)
            modules = data.get("modules", [])
        except:
            modules = []

        # 2. Fetch help for each
        knowledge_parts = []
        for m in modules:
            try:
                help_text = await self._tools_helper.get_module_help(m)
                knowledge_parts.append(f"--- Help for {m} ---\n{help_text}\n")
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
                parts=[types.Part(text=f"Retrieved context for {len(modules)} modules.")]
            )
        )

def create_debug_structured_adk_agent_v9(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 29: Module Proposal -> Deterministic Retrieval -> Solver.
    Exclusively uses get_module_help.
    """

    # Determine Model
    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model = model_name

    # 0. Setup
    setup_agent = SetupAgentCodeBased(
        name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper
    )

    # 0.2 Sanitizer
    prompt_sanitizer_agent = PromptSanitizerAgent(
        model=model,
        include_contents='none',
        output_key="sanitized_user_request",
    )

    # 1. Module Proposer (Hallucinated Guess -> Search Query)
    # This agent proposes WHICH modules to look at.
    module_proposer = LlmAgent(
        name="module_proposer",
        model=model,
        output_key="relevant_modules_json",
        output_schema=RelevantModules,
        include_contents='none',
        instruction=(
            """You are the API Surface Cartographer. 
Analyze the following request and propose a list of fully qualified Python module paths that might contain the classes or functions needed to solve it.
Request: {sanitized_user_request}

**Guidelines:**
- Propose modules from the library being used (e.g. `google.adk.agents`).
- If you need to implement a subclass, propose the parent class's module.
- Output ONLY the JSON list of modules."""
        )
    )

    # 2. Deterministic Fetcher (The Truth Grounder)
    fetcher_agent = DeterministicKnowledgeAgent(
        name="knowledge_fetcher",
        tools_helper=tools_helper
    )

    # 3. The Solver (Zero-Tool, Pure reasoning over provided context)
    solver_agent = LlmAgent(
        name="solver_agent",
        model=model,
        tools=[], # NO TOOLS ALLOWED. Must use provided context.
        include_contents='none',
        output_key="candidate_response",
        before_agent_callback=input_guard_callback,
        instruction=(
            """You are the Expert Codebase Solver. 
Request: {sanitized_user_request}

**CONTEXT (API Truth):**
{knowledge_context}

**STRICT PROTOCOL:**
1. **Analyze:** Carefully read the provided API help above.
2. **Strict Verification:** Identify the EXACT field names and method signatures from the context.
3. **Implement:** Write the final implementation.
   - You MUST use the types and attributes shown in the context.
   - Do NOT hallucinate attributes (like `.input`) if they are not in the context.
   - If a class you need is MISSING from the context, YOU MUST DEFINE IT yourself.

Output reasoning then the Python code in a block."""
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
        name="deterministic_retrieval_solver",
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

def create_statistical_v9_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 29 (ADK_STATISTICAL_V9).
    """
    name_prefix="ADK_STATISTICAL_V9"
    folder_prefix="adk_stat_v9_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v9(
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

