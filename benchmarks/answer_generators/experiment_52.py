"""
Experiment 52: Statistical Discovery V32 (Specialized Expert Delegation).
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
from benchmarks.answer_generators.experiment_49 import create_debug_structured_adk_agent_v29, _create_prismatic_retrieval_agents_v29
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedTeardownAgent, RotatingKeyGemini

# --- Expert Tool Wrappers --- 

def create_coding_expert_tool(tools_helper, model_name, api_key_manager) -> FunctionTool:
    """Wraps the V29 Coding Specialist as a tool."""
    # We create the agent inside the tool to ensure fresh state if needed,
    # but reuse the logic wholesale.
    coding_agent = create_debug_structured_adk_agent_v29(tools_helper, model_name, api_key_manager)

    async def run_coding_specialist(tool_context: ToolContext) -> str:
        """
        Runs the V29 Coding Specialist. 
        Use this for any request involving implementing agents, fixing code, or writing Python scripts.
        """
        ctx = tool_context._invocation_context
        # Use the sub-agent execution pattern with manual state propagation
        result_str = "Error: No code generated."
        async for event in coding_agent.run_async(ctx):
            if event.actions and event.actions.state_delta:
                ctx.session.state.update(event.actions.state_delta)
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        result_str = part.text
        
        # Ensure the finalizer sees the result
        ctx.session.state["final_expert_output"] = result_str
        return "Task completed by coding specialist."

    return FunctionTool(run_coding_specialist)

def create_knowledge_expert_tool(tools_helper, model) -> FunctionTool:
    """Wraps a new Knowledge Specialist as a tool."""
    
    retrieval_agents = _create_prismatic_retrieval_agents_v29(tools_helper, model)
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
    knowledge_agent = SequentialAgent(
        name="knowledge_specialist",
        sub_agents=[*retrieval_agents, qa_solver]
    )

    async def run_knowledge_specialist(tool_context: ToolContext) -> str:
        """
        Runs the Knowledge Specialist.
        Use this for Multiple Choice questions or API understanding questions.
        """
        ctx = tool_context._invocation_context
        result_str = "Error: No answer generated."
        async for event in knowledge_agent.run_async(ctx):
            if event.actions and event.actions.state_delta:
                ctx.session.state.update(event.actions.state_delta)
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        result_str = part.text
        
        ctx.session.state["final_expert_output"] = result_str
        return "Task completed by knowledge specialist."

    return FunctionTool(run_knowledge_specialist)

class ExpertResponseFinalizer(Agent):
    """Packages the expert output into the correct benchmark format."""
    def __init__(self, tools_helper, **kwargs):
        super().__init__(**kwargs)
        self._tools_helper = tools_helper

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        output_str = ctx.session.state.get("final_expert_output", "")
        agent_code = ctx.session.state.get("agent_code", "")
        
        candidate_data = {}
        is_json = False
        try:
            # Try to extract JSON if it's wrapped in markdown
            clean = output_str
            if "```json" in clean: clean = clean.split("```json")[1].split("```")[0]
            elif "```" in clean: clean = clean.split("```")[1].split("```")[0]
            candidate_data = json.loads(clean.strip())
            is_json = True
        except: pass

        final_json = "{}"
        
        # Heuristic 1: Multiple Choice (Has "answer" key)
        if is_json and "answer" in candidate_data:
            ans = candidate_data.get("answer", "E")
            rat = candidate_data.get("rationale", output_str[:200])
            final_json = json.dumps({"answer": ans, "rationale": rat, "benchmark_type": "multiple_choice"})
            
        # Heuristic 2: API Understanding (Has "fully_qualified_class_name" key)
        elif is_json and "fully_qualified_class_name" in candidate_data:
            code = candidate_data.get("code", "Unknown")
            fqn = candidate_data.get("fully_qualified_class_name", "Unknown")
            rat = candidate_data.get("rationale", output_str[:200])
            final_json = json.dumps({"code": code, "fully_qualified_class_name": fqn, "rationale": rat, "benchmark_type": "api_understanding"})
            
        # Heuristic 3: Coding (Default fallback)
        else:
            if not agent_code:
                match = re.search(r"```python\n(.*?)\n```", output_str, re.DOTALL)
                agent_code = match.group(1) if match else output_str
            
            self._tools_helper.write_file("my_agent.py", agent_code)
            # Default to fix_error type for coding tasks, but include raw output for safety
            final_json = json.dumps({"code": agent_code, "rationale": "Expert implementation.", "benchmark_type": "fix_error"})

        # IMPORTANT: Save to session state so TeardownAgent (which runs last) can find it.
        ctx.session.state["final_response"] = final_json

        yield Event(author=self.name, content=types.Content(role="model", parts=[types.Part(text=final_json)]))

def create_debug_structured_adk_agent_v32(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 52: V32 - The "Strict Delegator" with robust state propagation.
    """
    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model = model_name

    # 1. Expert Tools
    coding_tool = create_coding_expert_tool(tools_helper, model_name, api_key_manager)
    knowledge_tool = create_knowledge_expert_tool(tools_helper, model)

    # 2. Delegator
    delegator_agent = LlmAgent(
        name="delegator_agent",
        model=model,
        tools=[coding_tool, knowledge_tool],
        include_contents='none', # Minimal routing context
        instruction=(
            "You are the Request Router. Clasify the user request and call the correct expert.\n" 
            "1. Coding Requests: Call `run_coding_specialist`.\n"
            "2. Knowledge/QA Requests: Call `run_knowledge_specialist`.\n"
            "Classification is critical. Call exactly one tool."
        ),
    )

    # 3. Root Pipeline
    setup_agent = SetupAgentCodeBased(name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)
    prompt_sanitizer_agent = PromptSanitizerAgent(model=model, include_contents='none', output_key="sanitized_user_request")
    finalizer = ExpertResponseFinalizer(name="finalizer", tools_helper=tools_helper)
    teardown_agent = CodeBasedTeardownAgent(name="teardown_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)

    return SequentialAgent(
        name="adk_statistical_v32",
        sub_agents=[setup_agent, prompt_sanitizer_agent, delegator_agent, finalizer, teardown_agent],
    )

def create_statistical_v32_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """Factory for Experiment 52."""
    name_prefix="ADK_STATISTICAL_V32"
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_stat_v32_"))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root/"venv")
    agent = create_debug_structured_adk_agent_v32(tools_helper, model_name, api_key_manager)
    return AdkAnswerGenerator(agent=agent, name=f"{name_prefix}({model_name})", setup_hook=setup_hook, api_key_manager=api_key_manager, model_name=model_name)
