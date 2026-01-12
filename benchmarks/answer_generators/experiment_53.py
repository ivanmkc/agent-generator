"""
Experiment 53: Statistical Discovery V33 (Fast Retrieval).
Optimizes V32 by replacing the LLM-based Context Expander with a deterministic code-based agent.
"""

from pathlib import Path
import tempfile
import json
import re
from typing import AsyncGenerator

from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from google.adk.agents import LlmAgent, SequentialAgent, Agent
from google.adk.tools import FunctionTool, ToolContext
from google.adk.events import Event
from google.genai import types
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook
from benchmarks.answer_generators.experiment_49 import create_debug_structured_adk_agent_v29
from benchmarks.answer_generators.experiment_52 import create_coding_expert_tool, ExpertResponseFinalizer
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedTeardownAgent, RotatingKeyGemini, DocstringFetcherAgent


class ContextExpanderCodeBased(Agent):
    """
    Deterministically expands the relevant modules using the associations database.
    Replaces the slow LLM-based ContextExpander.
    """
    def __init__(self, tools_helper: AdkTools, **kwargs):
        super().__init__(**kwargs)
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        # 1. Load current seeds
        raw_json = ctx.session.state.get("relevant_modules_json", '{"modules": []}')
        try:
            current_modules = json.loads(raw_json).get("modules", [])
        except:
            current_modules = []
            
        if not current_modules:
             yield Event(author=self.name, content=types.Content(role="model", parts=[types.Part(text="No seeds to expand.")]))
             return

        # 2. Expand using associations
        expanded_set = set(current_modules)
        
        yield Event(author=self.name, content=types.Content(role="model", parts=[types.Part(text=f"Starting expansion for seeds: {current_modules}")]))
        
        for seed in current_modules:
            try:
                # Call the tool directly
                assoc_str = self._tools_helper.get_api_associations(seed)
                
                # Parse the output. 
                # Format: "- target_module (Prob: 0.95, Support: 10)"
                matches = re.findall(r"- ([^\s]+) \(Prob: ([0-9.]+),", assoc_str)
                found = []
                for mod_name, prob in matches:
                    if float(prob) >= 0.5: # Threshold
                        expanded_set.add(mod_name)
                        found.append(mod_name)
                
                if found:
                    yield Event(author=self.name, content=types.Content(role="model", parts=[types.Part(text=f"Found associations for {seed}: {found}")]))
                else:
                    yield Event(author=self.name, content=types.Content(role="model", parts=[types.Part(text=f"No associations found for {seed}.")]))
                        
            except Exception as e:
                yield Event(author=self.name, content=types.Content(role="model", parts=[types.Part(text=f"Error expanding {seed}: {e}")]))

        # 3. Update State
        new_list = list(expanded_set)
        ctx.session.state["relevant_modules_json"] = json.dumps({"modules": new_list})
        
        yield Event(
            author=self.name, 
            content=types.Content(
                role="model", 
                parts=[types.Part(text=f"Final module set: {new_list}")]
            )
        )

def _create_fast_prismatic_retrieval_agents_v33(tools_helper: AdkTools, model) -> list[Agent]:
    """
    Creates the fast retrieval chain: LLM Seed -> Code Expander -> Docstring Fetcher.
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

    # 1. Seed Selector (LLM) - Kept because it requires semantic understanding
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

    # 2. Context Expander (Code) - Replaces LLM
    context_expander_agent = ContextExpanderCodeBased(
        name="context_expander_agent",
        tools_helper=tools_helper
    )
    
    # 3. Docstring Fetcher (Code)
    docstring_fetcher_agent = DocstringFetcherAgent(
        name="docstring_fetcher_agent", tools_helper=tools_helper
    )
    
    return [seed_selector_agent, context_expander_agent, docstring_fetcher_agent]

class RoutingDelegatorAgent(Agent):
    """
    A custom agent that routes the request to either the Coding or Knowledge expert
    and YIELDS all sub-agent events to the parent runner for visibility.
    """
    def __init__(self, model, coding_agent: Agent, knowledge_agent: Agent, **kwargs):
        super().__init__(**kwargs)
        self._router = LlmAgent(
            name="router",
            model=model,
            include_contents='none',
            instruction=(
                "You are the Request Router. Classify the user request.\n"
                "1. Coding Requests: User wants to implement an agent, fix code, or write scripts.\n"
                "2. Knowledge/QA Requests: User asks a question about ADK, multiple choice, or API definitions.\n"
                "Output ONLY the word 'CODING' or 'KNOWLEDGE'."
            )
        )
        self._coding_agent = coding_agent
        self._knowledge_agent = knowledge_agent

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        # 1. Route
        route_decision = ""
        async for event in self._router.run_async(ctx):
            yield event # Show the routing thought/result
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        route_decision += part.text
        
        target_agent = self._knowledge_agent
        if "CODING" in route_decision.upper():
            target_agent = self._coding_agent
        
        # 2. Delegate and YIELD ALL EVENTS
        result_str = ""
        async for event in target_agent.run_async(ctx):
            yield event
            if event.actions and event.actions.state_delta:
                 ctx.session.state.update(event.actions.state_delta)
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        result_str = part.text
        
        ctx.session.state["final_expert_output"] = result_str

def create_debug_structured_adk_agent_v33(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 53: V33 - Fast Retrieval Delegation (Refactored for Visibility).
    """
    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model = model_name

    # 1. Experts (Inner agents)
    coding_agent = create_debug_structured_adk_agent_v29(tools_helper, model_name, api_key_manager)
    
    retrieval_agents = _create_fast_prismatic_retrieval_agents_v33(tools_helper, model)
    qa_solver = LlmAgent(
        name="qa_solver",
        model=model,
        include_contents='none',
        instruction=(
            """You are the ADK Knowledge Expert.
Request: {sanitized_user_request}
CONTEXT:
{knowledge_context}

GOAL: Answer the question accurately.
- MCQs: Output JSON `{\"answer\": \"A\", \"rationale\": \"...\"}`
- API: Output JSON `{\"code\": \"...\", \"fully_qualified_class_name\": \"...\", \"rationale\": \"...\"}`
"""
        )
    )
    knowledge_agent = SequentialAgent(name="knowledge_specialist", sub_agents=[*retrieval_agents, qa_solver])

    # 2. Delegator
    delegator_agent = RoutingDelegatorAgent(
        name="delegator_agent",
        model=model,
        coding_agent=coding_agent,
        knowledge_agent=knowledge_agent
    )

    # 3. Root Pipeline
    setup_agent = SetupAgentCodeBased(name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)
    prompt_sanitizer_agent = PromptSanitizerAgent(model=model, include_contents='none', output_key="sanitized_user_request")
    finalizer = ExpertResponseFinalizer(name="finalizer", tools_helper=tools_helper)
    teardown_agent = CodeBasedTeardownAgent(name="teardown_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)

    return SequentialAgent(
        name="adk_statistical_v33",
        sub_agents=[setup_agent, prompt_sanitizer_agent, delegator_agent, finalizer, teardown_agent],
    )

def create_statistical_v33_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """Factory for Experiment 53."""
    name_prefix="ADK_STATISTICAL_V33"
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_stat_v33_"))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root/"venv")
    agent = create_debug_structured_adk_agent_v33(tools_helper, model_name, api_key_manager)
    return AdkAnswerGenerator(agent=agent, name=f"{name_prefix}({model_name})", setup_hook=setup_hook, api_key_manager=api_key_manager, model_name=model_name)
