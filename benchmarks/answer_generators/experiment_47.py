"""
Experiment 47: Statistical Discovery V27 (BaseAgent Fallback).
"""

from pathlib import Path
import tempfile
import os
import subprocess
import json

from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from google.adk.agents import LlmAgent, SequentialAgent, Agent
from google.adk.tools import FunctionTool, ToolContext
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedRunner, CodeBasedFinalVerifier, CodeBasedTeardownAgent, RotatingKeyGemini, DocstringFetcherAgent
from benchmarks.answer_generators.debug_adk_agents import input_guard_callback
from benchmarks.answer_generators.adk_schemas import RelevantModules
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook

def _create_index_retrieval_agents_v27(tools_helper: AdkTools, model: str | RotatingKeyGemini) -> list[Agent]:
    """
    Creates index-based retrieval agents.
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

def create_debug_structured_adk_agent_v27(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 47: V26 + BaseAgent Fallback.
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

    retrieval_agents = _create_index_retrieval_agents_v27(tools_helper, model)

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

8. **VALIDATION TABLE (MANDATORY):**
   Before writing code, output a Markdown table:
   | Check Type | Target | In Context? | Decision | 
   | :--- | :--- | :--- | :--- |
   | Class | BaseAgent | YES | Inherit |
   | Arg | BaseAgent.name | YES | Pass to super |
   | Arg | BaseAgent.model | NO | **DO NOT PASS** |

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
        name="base_agent_solver",
        sub_agents=[
            setup_agent,
            prompt_sanitizer_agent,
            *retrieval_agents,
            solver_agent,
            code_based_runner,
            final_verifier,
            teardown_agent,
        ],
    )

    return agent_obj

def create_statistical_v27_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 47 (ADK_STATISTICAL_V27).
    """
    name_prefix="ADK_STATISTICAL_V27"
    folder_prefix="adk_stat_v27_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    
    # Use shared setup hook
    setup_hook = create_standard_setup_hook(
        workspace_root=workspace_root,
        adk_branch=adk_branch,
        name_prefix=name_prefix
    )

    # Defer agent creation to runtime if needed, but here we create it eagerly
    # Note: setup_utils handles venv creation, so we pass that path
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v27(
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
