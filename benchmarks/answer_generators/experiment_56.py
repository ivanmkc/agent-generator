"""
Experiment 56: Statistical Discovery V36 (Strict Signature Verification).
Builds on V35 with enhanced Verification Planner to prevent signature mismatches.
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
from benchmarks.answer_generators.experiment_55 import LoggedDocstringFetcherAgent, VerificationPlanParser, SmartRunAnalyst, _create_logged_retrieval_agents

# --- Enhanced Agents ---

class StrictVerificationPlannerAgent(LlmAgent):
    """
    V36 Upgrade: Enforces function signature preservation in the sanitized request.
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
                
                "**Task 1: Sanitize Request**\n"
                "Remove operational tool instructions (e.g., 'use write_file', 'run agent'). "
                "CRITICAL: You MUST preserve all Python function signatures, class names, and variable names exactly as requested. "
                "If the user asks for `def create_agent(model_name: str)`, do NOT simplify it to `create_agent`. "
                
                "**Task 2: Verification Plan**\n"
                "Create a runtime test to verify the code works.\n"
                "   - `test_prompt`: A string prompt to send to the created agent (e.g. 'Hello').\n"
                "   - `expected_output_regex`: A regex pattern to validate the agent's stdout.\n"
                "   - `rationale`: Explain how this test proves the code meets requirements.\n"
                
                "Output JSON: {sanitized_user_request, test_prompt, expected_output_regex, rationale}. "
            ),
            **kwargs
        )

def create_structured_adk_agent_v36(
    tools_helper: AdkTools,
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
) -> SequentialAgent:
    """
    Experiment 56: V36 Coding Specialist.
    """
    if api_key_manager:
        model = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)
        model_flash = RotatingKeyGemini(model="gemini-2.5-flash", api_key_manager=api_key_manager)
    else:
        model = model_name
        model_flash = "gemini-2.5-flash"

    # 1. Setup (Standard)
    setup_agent = SetupAgentCodeBased(
        name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper
    )

    # 2. Plan & Verify (V36 UPGRADE)
    planner = StrictVerificationPlannerAgent(model=model_flash, output_key="verification_plan_json")
    plan_parser = VerificationPlanParser(name="plan_parser")

    # 3. Retrieval (Logged - Same as V35)
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
            """You are the Expert Codebase Solver. "
            "Request: {sanitized_user_request}\n"

            "**API TRUTH CONTEXT:**\n"
            "{knowledge_context}"

            "**CURRENT STATE:**\n"
            "Previous Code: "
            "```python\n"
            "{agent_code}"
            "```\n"
            "Feedback/Errors: "
            "{analysis_feedback}"

            "**STRICT IMPLEMENTATION RULES:**\n"
            "1. **Signature Match:** You MUST implement the EXACT function signatures and class names requested. Do not change argument names or types.\n"
            "2. **Source of Truth:** Use the API Context for imports and class attributes.\n"
            "3. **Inheritance:** Inherit from `google.adk.agents.BaseAgent` unless specified otherwise.\n"

            "**OUTPUT FORMAT:**\n"
            "1. Reasoning text (analyzing requirements and signatures).\n"
            "2. The Python code block:\n"
            "```python\n"
            "...\n"
            "```\n"
            "Do NOT wrap the output in JSON."""
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
        max_iterations=4, 
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
        name="v36_coding_specialist",
        sub_agents=[
            # Setup removed (handled by root)?? 
            # Wait, in V35 we decided to keep it self-contained for the coding specialist 
            # OR wrap it. Let's look at the factory function below.
            # Ideally the specialist is just the logic.
            planner,
            plan_parser,
            *retrieval_agents,
            implementation_loop,
            final_verifier,
            # Teardown removed (handled by root)
        ],
    )

    return agent_obj


def create_statistical_v36_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None,
    adk_branch: str = "v1.20.0",
) -> AdkAnswerGenerator:
    """
    Factory for Experiment 56.
    """
    name_prefix="ADK_STATISTICAL_V36"
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_stat_v36_"))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root/"venv")
    
    if api_key_manager:
        model_flash = RotatingKeyGemini(model="gemini-2.5-flash", api_key_manager=api_key_manager)
    else:
        model_flash = "gemini-2.5-flash"

    # 1. Coding Agent (V36)
    coding_agent = create_structured_adk_agent_v36(tools_helper, "gemini-2.5-pro", api_key_manager)

    # 2. Knowledge Agent (Reuse V33/V35 logic)
    retrieval_agents = _create_logged_retrieval_agents(tools_helper, model_flash)
    
    qa_solver = LlmAgent(
        name="qa_solver",
        model=model_flash,
        include_contents='none',
        instruction=(
            """You are the ADK Knowledge Expert.\n"
            "Request: {sanitized_user_request}\n"
            "CONTEXT:\n"
            "{knowledge_context}"

            "GOAL: Answer the question accurately.\n"
            "- If it's a Multiple Choice Question: Output JSON `{\"answer\": \"A\", \"rationale\": \"...\"}`\n"
            "- If it's an API Question: Output JSON `{\"code\": \"...\", \"fully_qualified_class_name\": \"...\", \"rationale\": \"...\"}`\n"
            "- If it's a Bug Fix/Coding Task: Output JSON `{\"code\": \"...\", \"rationale\": \"...\"}`\n"""
        )
    )
    knowledge_agent = SequentialAgent(name="knowledge_specialist", sub_agents=[*retrieval_agents, qa_solver])

    # 3. Delegator
    delegator_agent = RoutingDelegatorAgent(
        name="delegator_agent",
        model=model_flash,
        coding_agent=coding_agent,
        knowledge_agent=knowledge_agent
    )

    # 4. Root Pipeline
    setup_agent = SetupAgentCodeBased(name="setup_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)
    
    prompt_sanitizer = PromptSanitizerAgent(model=model_flash, include_contents='none', output_key="sanitized_user_request")
    
    finalizer = ExpertResponseFinalizer(name="finalizer", tools_helper=tools_helper)
    teardown = CodeBasedTeardownAgent(name="teardown_agent", workspace_root=tools_helper.workspace_root, tools_helper=tools_helper)

    agent = SequentialAgent(
        name="adk_statistical_v36",
        sub_agents=[setup_agent, prompt_sanitizer, delegator_agent, finalizer, teardown]
    )

    return AdkAnswerGenerator(agent=agent, name=f"{name_prefix}(Mixed)", setup_hook=setup_hook, api_key_manager=api_key_manager, model_name="mixed")

