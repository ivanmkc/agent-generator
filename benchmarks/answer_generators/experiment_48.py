"""
Experiment 48: Statistical Discovery V28 (BaseAgent Fallback + Error Recovery Loop).
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

def _create_index_retrieval_agents_v28(tools_helper: AdkTools, model: str | RotatingKeyGemini) -> list[Agent]:
    """
    Creates index-based retrieval agents (Same as V27).
    """
    # Load index content
    index_path = Path("benchmarks/adk_index.yaml")
    if index_path.exists():
        with open(index_path, "r") as f:
            adk_index_content = f.read()
    else:
        adk_index_content = "Error: adk_index.yaml not found."

    def save_relevant_modules(modules: list[str], tool_context: ToolContext) -> str:
        """Saves the list of relevant modules to session state."""
        tool_context.session.state["relevant_modules_json"] = json.dumps(
            {"modules": modules}
        )
        return f"Saved {len(modules)} modules."

    save_modules_tool = FunctionTool(save_relevant_modules)

    module_selector_agent = LlmAgent(
        name="module_selector_agent",
        model=model,
        tools=[save_modules_tool],
        include_contents="none",
        instruction=(
            f"You are the Module Selector Agent. Use the provided index to select relevant modules.\n"
            f"Index:\n{adk_index_content}\n"
            "Request: {sanitized_user_request}\n"
            "Analyze the request and select the modules.\n"
            "**TARGETS:** `google.adk.agents.base_agent`, `google.adk.events`, `google.genai.types`.\n"
            "Use the `save_relevant_modules` tool."
        ),
    )
    
    docstring_fetcher_agent = DocstringFetcherAgent(
        name="docstring_fetcher_agent", tools_helper=tools_helper
    )
    
    return [module_selector_agent, docstring_fetcher_agent]

def create_debug_structured_adk_agent_v28(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 48: V27 + Error Recovery Loop.
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

    retrieval_agents = _create_index_retrieval_agents_v28(tools_helper, model)

    # 1. The Solver (Candidate Creator)
    # Modified instructions to handle feedback loop
    solver_agent = LlmAgent(
        name="solver_agent",
        model=model,
        tools=[], 
        include_contents='none', # Stateless between iterations
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

**TASK:**
1. If this is the first run (Feedback is empty), implement the solution from scratch.
2. If there is Feedback, analyze the errors in the "Previous Code" and fix them.

**STRICT IMPLEMENTATION RULES:**
1. **Source of Truth:** You MUST use the provided context above as the ONLY source for API signatures and fields.
2. **Inheritance:** Inherit from `google.adk.agents.BaseAgent`.
3. **CONSTRUCTOR (CRITICAL):** 
   - Call `super().__init__(name=name)`.
   - Do **NOT** pass `model` or `instruction` to `super()`. BaseAgent does not accept them.
   - If you need to store `model`, do `self._model = model_name`.

4. **ABSTRACT METHODS:** Override `_run_async_impl(self, ctx) -> AsyncGenerator[Event, None]`.

5. **INPUT ACCESS:**
   - Access: `ctx.user_content.parts[0].text`.
   - Check if `ctx.user_content` is None.

6. **EVENT CONSTRUCTION:**
   - Import: `from google.genai import types`
   - Yield `google.adk.events.Event`.
   - **Fields:**
     - `author="logic_agent"`.
     - `content=types.Content(parts=[types.Part(text="My Response")])`.

7. **SIGNATURE GUARD:**
   - Signature: `def create_agent(model_name: str) -> BaseAgent:`.

**OUTPUT FORMAT:**
1. Reasoning text (If fixing, explain what you fixed).
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

    # 2. The Analyst (Decides whether to loop)
    exit_loop_tool = FunctionTool(exit_loop)
    
    # We need a tool to read the logs if they are truncated, but for now we rely on the summary passed in context.
    # CodeBasedRunner saves 'run_output' to session state.
    
    run_analyst = LlmAgent(
        name="run_analyst",
        model=model,
        tools=[exit_loop_tool],
        include_contents='none',
        output_key="analysis_feedback",
        instruction=(
            """You are the Run Analyst.
**Execution Logs:**
{run_output}

**Task:**
1. Analyze the logs. Look for Python tracebacks, `ValidationError`, `ImportError`, or `AttributeError`.
2. Determine if the execution was successful.
   - **SUCCESS:** If the logs show the agent ran without crashing (Exit Code: 0) and produced the expected output (if visible), call `exit_loop()` immediately.
   - **FAILURE:** If there are errors, output a concise analysis of the error. Explain WHY it failed and suggest a fix. This feedback will be sent to the Solver.

**CRITICAL:** 
- If the logs look clean, YOU MUST CALL `exit_loop()`. Do not ask for permission.
- If there is an error, DO NOT call `exit_loop()`. Just output the analysis text."""
        )
    )

    # 3. The Loop
    implementation_loop = LoopAgent(
        name="implementation_loop",
        sub_agents=[solver_agent, code_based_runner, run_analyst],
        max_iterations=3, # Give it 3 tries to fix itself
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
        name="base_agent_solver_v28",
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

def create_statistical_v28_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 48 (ADK_STATISTICAL_V28).
    """
    name_prefix="ADK_STATISTICAL_V28"
    folder_prefix="adk_stat_v28_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    
    # Use shared setup hook
    setup_hook = create_standard_setup_hook(
        workspace_root=workspace_root,
        adk_branch=adk_branch,
        name_prefix=name_prefix
    )

    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v28(
        tools_helper=tools_helper, 
        model_name=model_name, 
        api_key_manager=api_key_manager
    )

    async def teardown_hook():
        pass

    return AdkAnswerGenerator(
        agent=agent, 
        name=f"{name_prefix}({model_name})", 
        setup_hook=setup_hook, 
        teardown_hook=teardown_hook, 
        api_key_manager=api_key_manager
    )

