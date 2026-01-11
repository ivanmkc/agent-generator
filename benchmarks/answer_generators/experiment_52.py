"""
Experiment 52: Statistical Discovery V32 (V29 wrapped in AgentTool).
"""

from pathlib import Path
import tempfile

from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import AgentTool
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook
from benchmarks.answer_generators.experiment_49 import create_debug_structured_adk_agent_v29

def create_debug_structured_adk_agent_v32(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 52: Wraps the entire V29 agent as an AgentTool.
    """
    
    # 1. Create the inner V29 agent (wholesale)
    # We pass the same tools_helper so it shares the environment config,
    # but the V29 agent has its own Setup/Teardown steps internally.
    v29_agent = create_debug_structured_adk_agent_v29(tools_helper, model_name, api_key_manager)
    
    # 2. Wrap it in an AgentTool
    # This allows the delegator to "call" the entire V29 pipeline as a single function.
    v29_tool = AgentTool(
        agent=v29_agent,
        skip_summarization=False, # We want the output summary
        include_plugins=True
    )

    # 3. Create the Delegator
    if api_key_manager:
        from benchmarks.answer_generators.adk_agents import RotatingKeyGemini
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
    else:
        model = model_name

    delegator_agent = LlmAgent(
        name="delegator_agent",
        model=model,
        tools=[v29_tool],
        include_contents='none', # Minimal context for the delegator
        instruction=(
            "You are a Supervisor Agent. Your goal is to fulfill the user's request by delegating to the specialized solver.\n"
            "1. Receive the request.\n"
            f"2. Call the `{v29_agent.name}` tool to execute the solution.\n"
            "3. Return the tool's output as your final answer."
        ),
    )

    # 4. Construct the V32 Agent
    # Since V29 handles its own Setup/Teardown, we just run the Delegator.
    # However, we need a root container.
    agent_obj = SequentialAgent(
        name="delegation_v32",
        sub_agents=[delegator_agent],
    )

    return agent_obj

def create_statistical_v32_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 52 (ADK_STATISTICAL_V32).
    """
    name_prefix="ADK_STATISTICAL_V32"
    folder_prefix="adk_stat_v32_"
    workspace_root = Path(tempfile.mkdtemp(prefix=folder_prefix))
    
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    venv_path = workspace_root / "venv"
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
    agent = create_debug_structured_adk_agent_v32(tools_helper, model_name, api_key_manager)

    async def teardown_hook():
        pass

    return AdkAnswerGenerator(
        agent=agent, 
        name=f"{name_prefix}({model_name})", 
        setup_hook=setup_hook, 
        teardown_hook=teardown_hook, 
        api_key_manager=api_key_manager
    )

