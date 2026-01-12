"""
Experiment 41: Statistical Discovery V21 (Super Call).
"""

from pathlib import Path
import tempfile
import os
import subprocess

from benchmarks.answer_generators.experiment_36 import create_debug_structured_adk_agent_v16, SmartKnowledgeAgent
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from google.adk.agents import LlmAgent, SequentialAgent, Agent
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedRunner, CodeBasedFinalVerifier, CodeBasedTeardownAgent, RotatingKeyGemini
from benchmarks.answer_generators.debug_adk_agents import input_guard_callback
from benchmarks.answer_generators.adk_schemas import RelevantModules

def create_debug_structured_adk_agent_v21(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 41: V20 + Mandatory Super Call.
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
- Response models (`google.adk.models`).

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
2. **Inheritance:** Prefer inheriting from `google.adk.agents.Agent`.
3. **CONSTRUCTOR (CRITICAL):**
   - You MUST implement `__init__(self, name: str)`.
   - You MUST call `super().__init__(name=name)` to initialize the Pydantic model correctly.
   - Do NOT skip the super call even if `BaseAgent` definition is missing.

4. **ABSTRACT METHODS (CRITICAL):**
   - Override `_run_async_impl(self, ctx) -> AsyncGenerator[Event, None]`.
   - It MUST be `async def`.
   - It MUST `yield` (not `return`) `Event` objects.

5. **EVENT USAGE:**
   - Yield `google.adk.events.Event`.
   - Use `content="My Text"` to send text.

6. **VALIDATION TABLE (MANDATORY):**
   Before writing code, output a Markdown table:
   | Check Type | Target | In Context? | Decision |
   | :--- | :--- | :--- | :--- |
   | Arg | Agent.name | YES | Keep |
   | Call | super().__init__ | N/A | **MUST CALL** |
   | Method | BaseAgent._run_async_impl | YES | **Override** |
   | Class | Event | YES | Yield It |

**OUTPUT FORMAT:**
1. Reasoning text.
2. Validation Table.
3. The Python code block:
```python
...
```
Do NOT wrap the output in JSON."""
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
        name="super_call_solver",
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

def create_statistical_v21_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 41 (ADK_STATISTICAL_V21).
    """
    name_prefix="ADK_STATISTICAL_V21"
    folder_prefix="adk_stat_v21_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v21(
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
