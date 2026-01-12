"""
Experiment 35: Statistical Discovery V15 (Class Preference).
"""

from pathlib import Path
import tempfile
import os
import subprocess

from benchmarks.answer_generators.experiment_34 import create_debug_structured_adk_agent_v14, SmartKnowledgeAgent
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from google.adk.agents import LlmAgent, SequentialAgent, Agent
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedRunner, CodeBasedFinalVerifier, CodeBasedTeardownAgent, RotatingKeyGemini
from benchmarks.answer_generators.debug_adk_agents import input_guard_callback
from benchmarks.answer_generators.adk_schemas import RelevantModules

def create_debug_structured_adk_agent_v15(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 35: V14 + Prefer 'Agent' over 'BaseAgent'.
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
- The main agent module (e.g. `google.adk.agents`).
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
2. **Inheritance Preference:** If you need to implement a custom agent, prefer inheriting from `google.adk.agents.Agent` (or `Agent` in context) instead of `BaseAgent`, unless `BaseAgent` is the only option listed.
3. **Type Conservatism:** Default to yielding `str` or `Event` for agent output. Do not invent `LlmResponse`.
4. **Missing Classes:** If `LogicAgent` is missing, define it locally.
5. **Keyword Only:** Initialize all Pydantic models with keyword arguments.

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
        name="class_preference_solver",
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

def create_statistical_v15_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 35 (ADK_STATISTICAL_V15).
    """
    name_prefix="ADK_STATISTICAL_V15"
    folder_prefix="adk_stat_v15_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v15(
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
