"""
Experiment 31: Statistical Discovery V11 (Schema Guard).
"""

from pathlib import Path
import tempfile
import os
import subprocess

from benchmarks.answer_generators.experiment_30 import create_debug_structured_adk_agent_v10, RobustKnowledgeAgent
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from google.adk.agents import LlmAgent, SequentialAgent, Agent
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedRunner, CodeBasedFinalVerifier, CodeBasedTeardownAgent, RotatingKeyGemini
from benchmarks.answer_generators.debug_adk_agents import input_guard_callback
from benchmarks.answer_generators.adk_schemas import RelevantModules

def create_debug_structured_adk_agent_v11(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 31: Robust 3-stage pipeline + Schema Guard.
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
2. **SCHEMA GUARD (Mandatory):** 
   - You MUST ONLY use field names (kwargs) that are explicitly listed in the 'Required' or 'Optional' fields for a class in the context.
   - **Ban:** Do NOT add `instruction` to a class initialization unless the context shows it has that field. 
   - Assume all classes are `extra='forbid'` (strict validation).

3. **AsyncGenerator Enforcement:** If a method returns `AsyncGenerator`, you MUST use `async def` and `yield`.

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
        name="schema_guarded_solver",
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

def create_statistical_v11_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 31 (ADK_STATISTICAL_V11).
    """
    name_prefix="ADK_STATISTICAL_V11"
    folder_prefix="adk_stat_v11_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v11(
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
