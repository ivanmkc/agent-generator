"""
Experiment 54: Statistical Discovery V34 (Pro Coding Expert).
Upgrades the Coding Specialist to Gemini Pro while keeping the Knowledge Specialist and Router on Flash.
Mains the Fast Retrieval logic from V33.
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
from benchmarks.answer_generators.experiment_52 import ExpertResponseFinalizer
from benchmarks.answer_generators.experiment_53 import ContextExpanderCodeBased, _create_fast_prismatic_retrieval_agents_v33, RoutingDelegatorAgent
from benchmarks.answer_generators.adk_agents import SetupAgentCodeBased, PromptSanitizerAgent, CodeBasedTeardownAgent, RotatingKeyGemini, DocstringFetcherAgent

def create_debug_structured_adk_agent_v34(
    tools_helper: AdkTools,
    model_name: str, # This will be used for Router/QA
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 54: V34 - Pro Coding Expert.
    """
    if api_key_manager:
        model_flash = RotatingKeyGemini(model="gemini-2.5-flash", api_key_manager=api_key_manager)
        model_pro = RotatingKeyGemini(model="gemini-2.5-pro", api_key_manager=api_key_manager)
    else:
        model_flash = "gemini-2.5-flash"
        model_pro = "gemini-2.5-pro"

    # 1. Experts
    # Upgrade Coding Specialist to PRO
    coding_agent = create_debug_structured_adk_agent_v29(tools_helper, "gemini-2.5-pro", api_key_manager)
    
    # Knowledge Specialist stays on FLASH (Fast & Cheap)
    retrieval_agents = _create_fast_prismatic_retrieval_agents_v33(tools_helper, model_flash)
    qa_solver = LlmAgent(
        name="qa_solver",
        model=model_flash,
        include_contents='none',
        instruction=(
            """You are the ADK Knowledge Expert.
Request: {sanitized_user_request}
TASK TYPE: {benchmark_type}
CONTEXT:
{knowledge_context}

GOAL: Answer the question accurately based ONLY on the TASK TYPE.
- If benchmark_type is 'multiple_choice': Output JSON `{\"answer\": \"A\", \"rationale\": \"...\"}`
- If benchmark_type is 'api_understanding': Output JSON `{\"code\": \"...\", \"fully_qualified_class_name\": \"...\", \"rationale\": \"...\"}`
- If benchmark_type is 'fix_error': Output JSON `{\"code\": \"...\", \"rationale\": \"...\"}`
"""
        )
    )
    knowledge_agent = SequentialAgent(name="knowledge_specialist", sub_agents=[*retrieval_agents, qa_solver])

    # 2. Delegator (Flash - Routing is easy)
    delegator_agent = RoutingDelegatorAgent(
        name="delegator_agent",
        model=model_flash,
        coding_agent=coding_agent,
        knowledge_agent=knowledge_agent
    )

    # 3. Root Pipeline
    setup_agent = SetupAgentCodeBased(name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)
    prompt_sanitizer_agent = PromptSanitizerAgent(model=model_flash, include_contents='none', output_key="sanitized_user_request")
    finalizer = ExpertResponseFinalizer(name="finalizer", tools_helper=tools_helper)
    teardown_agent = CodeBasedTeardownAgent(name="teardown_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)

    return SequentialAgent(
        name="adk_statistical_v34",
        sub_agents=[setup_agent, prompt_sanitizer_agent, delegator_agent, finalizer, teardown_agent],
    )

def create_statistical_v34_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """Factory for Experiment 54."""
    name_prefix="ADK_STATISTICAL_V34"
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_stat_v34_"))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root/"venv")
    # We ignore the passed model_name and use our Mixed-In strategy
    agent = create_debug_structured_adk_agent_v34(tools_helper, model_name, api_key_manager)
    return AdkAnswerGenerator(agent=agent, name=f"{name_prefix}(Mixed)", setup_hook=setup_hook, api_key_manager=api_key_manager, model_name="mixed")
