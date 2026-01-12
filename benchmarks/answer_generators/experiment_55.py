"""
Experiment 55: Statistical Discovery V35 (Verified Coding Expert).
Upgrades V34 to include:
1. True Verification: The Plan step now generates test prompts and expected behavior regexes.
2. Logged Fetching: The DocstringFetcher logs its internal "tool calls" for visibility.
"""

from pathlib import Path
import tempfile
import json
import re
import uuid
from typing import AsyncGenerator

from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from google.adk.agents import LlmAgent, SequentialAgent, Agent, LoopAgent, InvocationContext
from google.adk.tools import FunctionTool, ToolContext, exit_loop
from google.adk.events import Event
from google.genai import types
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook
from benchmarks.answer_generators.experiment_52 import ExpertResponseFinalizer
from benchmarks.answer_generators.experiment_53 import ContextExpanderCodeBased, RoutingDelegatorAgent
from benchmarks.answer_generators.adk_agents import (
    SetupAgentCodeBased, 
    PromptSanitizerAgent, 
    CodeBasedTeardownAgent, 
    RotatingKeyGemini, 
    CodeBasedRunner,
    CodeBasedFinalVerifier,
    RelevantModules
)
from benchmarks.answer_generators.debug_adk_agents import input_guard_callback

# --- 1. Logged Docstring Fetcher ---

class LoggedDocstringFetcherAgent(Agent):
    """
    Fetches help for selected modules using captured tools_helper.
    Logs "fake" tool calls to the event stream for visibility in traces.
    """
    def __init__(self, tools_helper: AdkTools, **kwargs):
        super().__init__(**kwargs)
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # 1. Retrieve selected modules from session state
        relevant_modules_json = ctx.session.state.get("relevant_modules_json", "{}")
        
        try:
            if isinstance(relevant_modules_json, str):
                if "```json" in relevant_modules_json:
                    relevant_modules_json = relevant_modules_json.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in relevant_modules_json:
                    relevant_modules_json = relevant_modules_json.split("```", 1)[1].split("```", 1)[0].strip()
                relevant_modules = RelevantModules.model_validate_json(relevant_modules_json)
            elif isinstance(relevant_modules_json, dict):
                    relevant_modules = RelevantModules.model_validate(relevant_modules_json)
            else:
                    relevant_modules = relevant_modules_json

        except Exception as e:
            ctx.session.state["knowledge_context"] = f"Error retrieving knowledge context: {e}"
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"Error parsing relevant modules: {e}")]
                )
            )
            return

        # 2. Fetch help for each module using captured tools_helper with LOGGING
        knowledge_context_parts = []
        for module_name in relevant_modules.modules:
            call_id = f"call_fetch_{uuid.uuid4().hex[:8]}"
            
            # Log Tool Call
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part(function_call=types.FunctionCall(
                        name="get_module_help",
                        args={"module_name": module_name},
                        id=call_id
                    ))]
                )
            )

            try:
                help_text = await self._tools_helper.get_module_help(module_name)
                knowledge_context_parts.append(f"--- Help for {module_name} ---\n{help_text}\n")
                
                # Log Tool Response
                yield Event(
                    invocation_id=ctx.invocation_id,
                    author=self.name,
                    content=types.Content(
                        role="tool",
                        parts=[types.Part(function_response=types.FunctionResponse(
                            name="get_module_help",
                            response={"result": f"(Fetched {len(help_text)} chars)"}, # Truncate log to save tokens, we have the data
                            id=call_id
                        ))]
                    )
                )

            except Exception as e:
                error_msg = f"Error fetching help for {module_name}: {e}"
                knowledge_context_parts.append(error_msg + "\n")
                
                # Log Tool Error
                yield Event(
                    invocation_id=ctx.invocation_id,
                    author=self.name,
                    content=types.Content(
                        role="tool",
                        parts=[types.Part(function_response=types.FunctionResponse(
                            name="get_module_help",
                            response={"error": str(e)},
                            id=call_id
                        ))]
                    )
                )

        full_context = "\n".join(knowledge_context_parts)
        
        # 3. Save to session state
        ctx.session.state["knowledge_context"] = full_context
        
        # 4. Yield output
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Fetched knowledge context for {len(relevant_modules.modules)} modules.")]
            )
        )

# --- 2. Verification Agents ---

class VerificationPlannerAgent(LlmAgent):
    """
    Replaces PromptSanitizer.
    Generates sanitized request AND a verification plan (test prompt + regex).
    """
    def __init__(self, model, **kwargs):
        super().__init__(
            name="verification_planner",
            model=model,
            tools=[],
            include_contents='none',
            instruction=(
                "You are the Verification Planner. "
                "Request: {user_request}\n"
                "Task 1: Sanitize the request. Remove instructions to use specific tools (run_adk_agent, write_file). Keep the core coding objective.\n"
                "Task 2: Create a verification plan.\n"
                "   - `test_prompt`: A string prompt to send to the created agent to verify it works.\n"
                "   - `expected_output_regex`: A regex pattern to validate the agent's stdout.\n"
                "   - `rationale`: Why you chose this test.\n"
                "Output JSON: {sanitized_user_request, test_prompt, expected_output_regex, rationale}."
            ),
            **kwargs
        )
    
    # We use a custom runner/callback logic or just rely on output_key to save specific fields?
    # ADK output_key only saves the whole string if it's a string.
    # We need to parse the JSON and save individual fields.
    # LlmAgent doesn't natively split JSON into state keys. 
    # We can use a `after_agent_callback` but for now let's just dump the whole JSON 
    # into a state key 'verification_plan_json' and have downstream agents parse it.
    # Wait, CodeBasedRunner expects 'verification_plan' text or 'agent_code'. 
    # Let's override `_run_async_impl` or use a wrapper?
    # Simplest: Just instruct it to output JSON and we'll have a `PlanParser` agent (code based) next?
    # Or just use the `before_agent_callback` of the NEXT agent to parse it.
    # Actually, `CodeBasedRunner` in `adk_agents.py` does loose regex matching on `verification_plan` key.
    # "Test Prompt: ... "
    # So if I output "Test Prompt: ... \n Expected Runtime Behavior: ..." it works with legacy `CodeBasedRunner`.
    # BUT I want `expected_output_regex` for my NEW `SmartRunAnalyst`.
    
    # Let's assume this agent saves to `verification_plan_json`.

class VerificationPlanParser(Agent):
    """
    Parses the JSON from VerificationPlannerAgent and sets individual state keys.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        raw = ctx.session.state.get("verification_plan_json", "")
        # Try to extract JSON
        try:
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            
            data = json.loads(raw)
            ctx.session.state["sanitized_user_request"] = data.get("sanitized_user_request", "")
            
            # Format legacy string for CodeBasedRunner (legacy compatibility)
            # Legacy runner looks for "Test Prompt: ..."
            legacy_plan = f"Test Prompt: {data.get('test_prompt', 'Hello')}\nExpected: {data.get('expected_output_regex', '')}"
            ctx.session.state["verification_plan"] = legacy_plan
            
            # Set explicit keys for SmartRunAnalyst
            ctx.session.state["test_prompt"] = data.get("test_prompt", "Hello")
            ctx.session.state["expected_output_regex"] = data.get("expected_output_regex", ".*")
            
            yield Event(author=self.name, content=types.Content(role="model", parts=[types.Part(text="Plan parsed and state updated.")]))
            
        except Exception as e:
            # Fallback
            ctx.session.state["sanitized_user_request"] = ctx.session.state.get("user_request", "")
            ctx.session.state["test_prompt"] = "Hello"
            ctx.session.state["expected_output_regex"] = ".*"
            yield Event(author=self.name, content=types.Content(role="model", parts=[types.Part(text=f"Plan parsing failed: {e}. Used fallbacks.")]))


class SmartRunAnalyst(LlmAgent):
    """
    Analyzes logs using the expected regex/behavior.
    """
    def __init__(self, model, **kwargs):
        super().__init__(
            name="smart_run_analyst",
            model=model,
            tools=[FunctionTool(exit_loop)],
            include_contents='none',
            output_key="analysis_feedback",
            instruction=(
                """You are the Smart Run Analyst.
**Expectation:**
Regex/Criteria: {expected_output_regex}

**Execution Logs:**
{run_output}

1. Check if the 'Stdout' in logs matches the Expectation.
2. Check for 'Stderr' errors.
3. If SUCCESS (Matches logic AND no crashes): Call `exit_loop()` immediately.
4. If FAILURE: Explain why (e.g., "Output 'foo' did not match regex 'bar'") and suggest a fix."""
            ),
            **kwargs
        )

# --- 3. Construction ---

def _create_logged_retrieval_agents(tools_helper: AdkTools, model) -> list[Agent]:
    """
    Same as V33 but with LoggedDocstringFetcherAgent.
    """
    # Load index content for seed selection
    index_path = Path("benchmarks/adk_index.yaml")
    if index_path.exists():
        with open(index_path, "r") as f:
            adk_index_content = f.read()
    else:
        adk_index_content = "Error: adk_index.yaml not found."

    def save_relevant_modules(modules: list[str], tool_context: ToolContext) -> str:
        tool_context.session.state["relevant_modules_json"] = json.dumps({"modules": modules})
        return f"Saved seeds: {modules}"

    save_modules_tool = FunctionTool(save_relevant_modules)

    seed_selector_agent = LlmAgent(
        name="seed_selector_agent",
        model=model,
        tools=[save_modules_tool],
        include_contents="none",
        instruction=(
            f"You are the Seed Selector. Based on the user request, pick the ONE or TWO most relevant primary ADK modules.\n"
            f"Index:\n{adk_index_content}\n"
            "Request: {sanitized_user_request}\n"
            "Use `save_relevant_modules` with just the seeds."
        ),
    )

    context_expander_agent = ContextExpanderCodeBased(
        name="context_expander_agent",
        tools_helper=tools_helper
    )
    
    # REPLACED
    docstring_fetcher_agent = LoggedDocstringFetcherAgent(
        name="docstring_fetcher_agent", tools_helper=tools_helper
    )
    
    return [seed_selector_agent, context_expander_agent, docstring_fetcher_agent]


def create_structured_adk_agent_v35(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 55: V35 Coding Specialist.
    """
    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
        # Use Flash for planning/analysis if Mixed logic isn't passed down?
        # The `model_name` passed here is usually Pro (from V34).
        # We want Flash for the non-coding parts.
        model_flash = RotatingKeyGemini(model="gemini-2.5-flash", api_key_manager=api_key_manager)
    else:
        model = model_name
        model_flash = "gemini-2.5-flash"

    # 1. Setup (Standard)
    setup_agent = SetupAgentCodeBased(
        name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper
    )

    # 2. Plan & Verify (Replaces PromptSanitizer)
    planner = VerificationPlannerAgent(model=model_flash, output_key="verification_plan_json")
    plan_parser = VerificationPlanParser(name="plan_parser")

    # 3. Retrieval (Logged)
    retrieval_agents = _create_logged_retrieval_agents(tools_helper, model_flash)

    # 4. Loop
    solver_agent = LlmAgent(
        name="solver_agent",
        model=model, # PRO MODEL
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
2. The Python code block:
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

    # Smart Analyst (Flash)
    run_analyst = SmartRunAnalyst(model=model_flash)

    implementation_loop = LoopAgent(
        name="implementation_loop",
        sub_agents=[solver_agent, code_based_runner, run_analyst],
        max_iterations=4 # Give it a chance to fix logic errors
    )

    # 5. Finalize
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
        name="prismatic_solver_v35",
        sub_agents=[
            setup_agent,
            planner,
            plan_parser,
            *retrieval_agents,
            implementation_loop,
            final_verifier,
            teardown_agent,
        ],
    )

    return agent_obj


def create_statistical_v35_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 55.
    Uses Mixed Model topology: Flash for Routing/QA, Pro for Coding.
    """
    name_prefix="ADK_STATISTICAL_V35"
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_stat_v35_"))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root/"venv")
    
    if api_key_manager:
        model_flash = RotatingKeyGemini(model="gemini-2.5-flash", api_key_manager=api_key_manager)
    else:
        model_flash = "gemini-2.5-flash"

    # 1. Coding Agent (The V35 Upgrade)
    # We pass "gemini-2.5-pro" explicitly for the solver
    coding_agent = create_structured_adk_agent_v35(tools_helper, "gemini-2.5-pro", api_key_manager)

    # 2. Knowledge Agent (Reuse V33 logic but with LOGGED retrieval)
    # Re-using _create_logged_retrieval_agents here to keep behavior consistent
    retrieval_agents = _create_logged_retrieval_agents(tools_helper, model_flash)
    
    qa_solver = LlmAgent(
        name="qa_solver",
        model=model_flash,
        include_contents='none',
        instruction=(
            """You are the ADK Knowledge Expert.
Request: {sanitized_user_request}
CONTEXT:
{knowledge_context}

GOAL: Answer the question accurately.
- If it's a Multiple Choice Question: Output JSON `{\"answer\": \"A\", \"rationale\": \"...\"}`
- If it's an API Question: Output JSON `{\"code\": \"...\", \"fully_qualified_class_name\": \"...\", \"rationale\": \"...\"}`
- If it's a Bug Fix/Coding Task: Output JSON `{\"code\": \"...\", \"rationale\": \"...\"}`
"""
        )
    )
    knowledge_agent = SequentialAgent(name="knowledge_specialist", sub_agents=[*retrieval_agents, qa_solver])

    # 3. Delegator
    delegator_agent = RoutingDelegatorAgent(
        name="delegator_agent",
        model=model_flash,
        coding_agent=coding_agent, # Use V35
        knowledge_agent=knowledge_agent
    )

    # 4. Root Pipeline (Note: V35 Coding Agent has its own Setup/Teardown, but Delegator needs wrapping for Knowledge path)
    # Actually, V35 Coding Agent is self-contained. Knowledge Agent is NOT (needs setup).
    # If we route to Coding Agent, it runs Setup. If we route to Knowledge, it expects Setup.
    # This is a flaw in previous Mixed architectures if Setup is inside the Coding Agent.
    # Let's check V34 (`experiment_54.py`).
    # V34 Structure: Root Setup -> Root Sanitizer -> Delegator -> Finalizer -> Teardown.
    # And V29 Coding Agent (used in V34) ALSO has Setup/Teardown.
    # This means Setup runs TWICE for coding tasks. 
    # V35 Fix: Remove Setup/Teardown from the INNER V35 Coding Agent and let the ROOT pipeline handle it.
    
    # Let's redefine create_structured_adk_agent_v35 to NOT include Setup/Teardown/Sanitizer/Finalizer
    # It should just be: Planner -> Retrieval -> Loop.
    
    # REDEFINITION OF INNER AGENT FOR MIXED PIPELINE:
    
    # 1. Planner & Parser
    planner = VerificationPlannerAgent(model=model_flash, output_key="verification_plan_json")
    plan_parser = VerificationPlanParser(name="plan_parser")
    
    # 2. Retrieval
    coding_retrieval = _create_logged_retrieval_agents(tools_helper, model_flash)
    
    # 3. Loop (Pro)
    solver = LlmAgent(
        name="solver_agent",
        model="gemini-2.5-pro" if not api_key_manager else RotatingKeyGemini(model="gemini-2.5-pro", api_key_manager=api_key_manager),
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
2. The Python code block:
```python
...
```
Do NOT wrap the output in JSON."""
        ),
    )
    
    code_runner = CodeBasedRunner(name="code_based_runner", tools_helper=tools_helper, model_name="gemini-2.5-pro")
    smart_analyst = SmartRunAnalyst(model=model_flash)
    
    loop = LoopAgent(
        name="implementation_loop",
        sub_agents=[solver, code_runner, smart_analyst],
        max_iterations=4
    )
    
    # 4. Final Verifier (Persists my_agent.py)
    final_verifier = CodeBasedFinalVerifier(name="final_verifier", tools_helper=tools_helper)

    coding_pipeline = SequentialAgent(
        name="v35_coding_specialist",
        sub_agents=[planner, plan_parser, *coding_retrieval, loop, final_verifier]
    )

    # ROOT PIPELINE
    setup_agent = SetupAgentCodeBased(name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)
    
    # Root sanitizer? No, VerificationPlanner does sanitization for Coding.
    # But Knowledge path needs it.
    # The Router needs the raw request or the sanitized one?
    # V34: Setup -> Sanitizer -> Delegator.
    # The Sanitizer in V34 outputs `sanitized_user_request`.
    # VerificationPlanner takes `user_request` and outputs `sanitized`.
    # If we run Sanitizer at root, VerificationPlanner can just take `sanitized_user_request` and produce Plan.
    
    prompt_sanitizer = PromptSanitizerAgent(model=model_flash, include_contents='none', output_key="sanitized_user_request")
    
    # Delegator
    delegator = RoutingDelegatorAgent(
        name="delegator_agent",
        model=model_flash,
        coding_agent=coding_pipeline,
        knowledge_agent=knowledge_agent
    )
    
    finalizer = ExpertResponseFinalizer(name="finalizer", tools_helper=tools_helper)
    teardown = CodeBasedTeardownAgent(name="teardown_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)

    agent = SequentialAgent(
        name="adk_statistical_v35",
        sub_agents=[setup_agent, prompt_sanitizer, delegator, finalizer, teardown]
    )

    return AdkAnswerGenerator(agent=agent, name=f"{name_prefix}(Mixed)", setup_hook=setup_hook, api_key_manager=api_key_manager, model_name="mixed")
