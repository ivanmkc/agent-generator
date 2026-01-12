"""
Experiment 25: Statistical Discovery V5 (V4 + read_file).
"""

from pathlib import Path
import tempfile
import os
import subprocess

from benchmarks.answer_generators.debug_adk_agents import create_debug_structured_adk_agent, input_guard_callback
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from google.adk.agents import LlmAgent, SequentialAgent, Agent
from google.adk.tools import FunctionTool, exit_loop
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedRunner, CodeBasedFinalVerifier, CodeBasedTeardownAgent, RotatingKeyGemini

def create_debug_structured_adk_agent_v5(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    retrieval_agents: list[Agent] = [],
    use_loop_history: bool = True,
) -> SequentialAgent:
    """
    Experiment 25: V4 logic but with read_file enabled.
    """

    # Bespoke Tools
    get_help_tool = FunctionTool(tools_helper.get_module_help)
    search_tool = FunctionTool(tools_helper.search_files)
    read_defs_tool = FunctionTool(tools_helper.read_definitions)
    
    # Standard tools
    write_tool = FunctionTool(tools_helper.write_file)
    replace_tool = FunctionTool(tools_helper.replace_text)
    
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

    # 1. The Solver (Proof of Knowledge)
    solver_agent = LlmAgent(
        name="solver_agent",
        model=model,
        tools=[get_help_tool, search_tool, read_defs_tool, write_tool, replace_tool],
        include_contents='default',
        output_key="candidate_response",
        before_agent_callback=input_guard_callback,
        instruction=(
            """You are the Expert Codebase Solver. 
Request: {sanitized_user_request}

**STRICT PROTOCOL:**
1. **Locate & Discover:** Use `search_files` to find files and `get_module_help` or `read_definitions` to inspect class/method signatures.
   - **IMPORT VERIFICATION:** You must verify the existence of modules and classes using these tools before importing them.
   
2. **PROOF OF KNOWLEDGE (Mandatory):**
   - Before writing ANY code, you must output a reasoning block that lists the EXACT fields and method signatures you found.
   - **Constraint:** If you need to access user data from a context object (e.g. `InvocationContext`), you MUST quote the field name (e.g. `user_content`) exactly as shown in `get_module_help` or `read_definitions`.
   - **Ban:** Do NOT use `context.input` or `context.request` unless you explicitly saw them in the tool output.

3. **Implement:** Write the code using *only* the proven signatures.
   - Do NOT read full file implementations; rely on the structural information from `get_module_help` and `read_definitions`.

Output reasoning (including Proof of Knowledge) then code."""
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
        name="debug_single_solver_v5",
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

def create_statistical_v5_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 25 (ADK_STATISTICAL_V5).
    """
    name_prefix="ADK_STATISTICAL_V5"
    folder_prefix="adk_stat_v5_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v5(
        tools_helper=tools_helper, 
        model_name=model_name, 
        api_key_manager=api_key_manager, 
        retrieval_agents=[], 
        use_loop_history=False
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
