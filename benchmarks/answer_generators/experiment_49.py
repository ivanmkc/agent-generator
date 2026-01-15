"""
Experiment 49: Statistical Discovery V29 (Association-Aware Retrieval).
"""

from pathlib import Path
import tempfile
import os
import subprocess
import json
import re

from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from google.adk.agents import LlmAgent, SequentialAgent, Agent, LoopAgent
from google.adk.tools import FunctionTool, ToolContext, exit_loop
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedRunner, CodeBasedFinalVerifier, CodeBasedTeardownAgent, RotatingKeyGemini, DocstringFetcherAgent
from benchmarks.answer_generators.debug_adk_agents import input_guard_callback
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook

def _create_prismatic_retrieval_agents_v29(tools_helper: AdkTools, model: str | RotatingKeyGemini) -> list[Agent]:
    """
    Creates association-aware retrieval agents.
    """
    # Load index content for seed selection
    index_path = Path("benchmarks/adk_index.yaml")
    if index_path.exists():
        with open(index_path, "r") as f:
            adk_index_content = f.read()
    else:
        adk_index_content = "Error: adk_index.yaml not found."

    def save_relevant_modules(modules: list[str], tool_context: ToolContext) -> str:
        """Saves the list of relevant modules to session state."""
        # Ensure we don't overwrite if expansion adds more
        existing = json.loads(tool_context.session.state.get("relevant_modules_json", '{"modules": []}'))
        new_list = list(set(existing["modules"] + modules))
        tool_context.session.state["relevant_modules_json"] = json.dumps({"modules": new_list})
        return f"Current module set: {new_list}"

    save_modules_tool = FunctionTool(save_relevant_modules)
    assoc_tool = FunctionTool(tools_helper.get_api_associations)

    # 1. Seed Selector: Picks the primary module
    seed_selector_agent = LlmAgent(
        name="seed_selector_agent",
        model=model,
        tools=[save_modules_tool],
        include_contents="none",
        instruction=(
            f"You are the Seed Selector. Based on the user request, pick the MOST relevant primary ADK module.\n"
            f"Index:\n{adk_index_content}\n"
            "Request: {sanitized_user_request}\n"
            "Use `save_relevant_modules` with just the one or two most central modules."
        ),
    )

    # 2. Context Expander: Uses statistical associations to find related modules
    context_expander_agent = LlmAgent(
        name="context_expander_agent",
        model=model,
        tools=[assoc_tool, save_modules_tool],
        include_contents="none",
        instruction=(
            "You are the Context Expander. Your goal is to find modules that are statistically likely to be used with the seeds.\n"
            "1. Look at the `relevant_modules_json` in the state (if visible, otherwise use your internal memory of the previous turn).\n"
            "2. For each seed module, call `get_api_associations` to find related components.\n"
            "3. Add the highly probable associations (Prob > 0.5) to the set using `save_relevant_modules`."
        ),
    )
    
    docstring_fetcher_agent = DocstringFetcherAgent(
        name="docstring_fetcher_agent", tools_helper=tools_helper
    )
    
    return [seed_selector_agent, context_expander_agent, docstring_fetcher_agent]

def create_debug_structured_adk_agent_v29(
    tools_helper: AdkTools,
    model_name: str | RotatingKeyGemini,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 49: V28 + Association-Aware Discovery.
    """

    if isinstance(model_name, str) and api_key_manager:
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

    retrieval_agents = _create_prismatic_retrieval_agents_v29(tools_helper, model)

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

**CURRENT STATE:**
Previous Code: 
```python
{agent_code}
```
Feedback/Errors: 
{analysis_feedback}

**STRICT IMPLEMENTATION RULES:**
1. **Source of Truth:** You MUST use the provided context above as the ONLY source for API signatures and fields.
2. **Inheritance:** Inherit from `google.adk.agents.BaseAgent`.

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

    run_analyst = LlmAgent(
        name="run_analyst",
        model=model,
        tools=[FunctionTool(exit_loop)],
        include_contents='none',
        output_key="analysis_feedback",
        instruction=(
            """You are the Run Analyst.
**Execution Logs:**
{run_output}

1. Analyze for crashes or validation errors.
2. If SUCCESS: Call `exit_loop()` immediately.
3. If FAILURE: Explain why and suggest a fix."""
        )
    )

    implementation_loop = LoopAgent(
        name="implementation_loop",
        sub_agents=[solver_agent, code_based_runner, run_analyst],
        max_iterations=3,
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
        name="prismatic_solver_v29",
        description="Agent for solving coding tasks.",
        sub_agents=[
            setup_agent,
            prompt_sanitizer_agent,
            *retrieval_agents,
            implementation_loop,
            final_verifier,
            teardown_agent,
        ],
    )

    return agent_obj

def create_statistical_v29_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 49 (ADK_STATISTICAL_V29).
    """
    name_prefix="ADK_STATISTICAL_V29"
    folder_prefix="adk_stat_v29_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v29(tools_helper, model_name, api_key_manager)

    async def teardown_hook():
        pass

    return AdkAnswerGenerator(
        agent=agent, 
        name=f"{name_prefix}({model_name})", 
        setup_hook=setup_hook, 
        teardown_hook=teardown_hook, 
        api_key_manager=api_key_manager,
        model_name=model_name
    )

