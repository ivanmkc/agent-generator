"""Experiment 67 module."""

# Experiment 67: Hybrid Specialist V47 (Routed Ranked Retrieval).
#
# Architecture:
# - Router: Classifies request as CODING or KNOWLEDGE.
# - Knowledge Expert: Hierarchical Ranked Retrieval + Single Step Solver.
#   **REVERTED TO V46:** Uses Shared History for high-fidelity context (Solver sees raw tool outputs).
# - Coding Expert: V29 Implementation Loop (Planner -> Iterative Fix Loop -> Verifier).
#   **MAINTAINED V47:** Uses Isolated State (Summary variables) to keep context clean.
# - Post-Processor: Formats final text result into structured JSON.

from pathlib import Path
import tempfile
import json
import re
import datetime
from typing import AsyncGenerator, Optional, List

from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager
from benchmarks.data_models import (
    GeneratedAnswer,
    BenchmarkGenerationError,
    FixErrorBenchmarkCase,
    ApiUnderstandingBenchmarkCase,
    MultipleChoiceBenchmarkCase,
    FixErrorAnswerOutput,
    ApiUnderstandingAnswerOutput,
    MultipleChoiceAnswerOutput,
    BaseBenchmarkCase,
    TraceLogEvent,
    TraceEventType,
)
from benchmarks.answer_generators.adk_schemas import VerificationPlan
from benchmarks.answer_generators.adk_context import adk_execution_context

from google.adk.agents import LlmAgent, SequentialAgent, Agent, InvocationContext, LoopAgent
from google.adk.events import Event
from google.adk.tools import FunctionTool, ToolContext, exit_loop
from google.genai import types
from benchmarks.answer_generators.setup_utils import create_standard_setup_hook
from benchmarks.answer_generators.adk_agents import (
    SetupAgentCodeBased,
    CodeBasedTeardownAgent,
    RotatingKeyGemini,
    CodeBasedRunner,
    CodeBasedFinalVerifier,
)
<<<<<<<< HEAD:experiments/experiment_67.py
from experiments.experiment_66 import PostProcessedAdkAnswerGenerator
========
from benchmarks.answer_generators.experiment_66.experiment_66 import PostProcessedAdkAnswerGenerator
>>>>>>>> 92bf5fe (Refactor answer generators into package structure and cleanup old experiments):benchmarks/answer_generators/experiment_67/experiment_67.py

# --- Retrieval Components ---


def _create_isolated_retrieval_loop(
    tools_helper: AdkTools, model, is_coding=False
) -> Agent:
    """
    Creates a ISOLATED Retrieval Loop that saves findings to session state.
    Used by Coding Expert.
    """

    def save_knowledge(summary: str, tool_context: ToolContext) -> str:
        """Saves the gathered API knowledge to session state."""
        tool_context.session.state["knowledge_context"] = summary
        return "Knowledge saved to session state."

    async def list_ranked_targets(
        page: int = 1, tool_context: ToolContext = None
    ) -> str:
        return tools_helper.list_ranked_targets(page=page)

    async def inspect_fqn(fqn: str, tool_context: ToolContext) -> str:
        return tools_helper.inspect_ranked_target(fqn)

    async def search_ranked_targets(
        query: str | list[str], page: int = 1, tool_context: ToolContext = None
    ) -> str:
        return tools_helper.search_ranked_targets(query, page=page)

    instruction = (
        "You are the Hierarchical Retrieval Agent. Your goal is to find relevant ADK classes/methods "
        "and SAVE a comprehensive summary to the session state.\n"
        "**ROLE:** Researcher ONLY. Do NOT write code. Do NOT implement the solution. Do NOT call exit_loop.\n"
        "**STRATEGY:**\n"
        "1. **BROWSE:** Call `list_ranked_targets(page=1)` to see top components.\n"
        "2. **SEARCH:** Use `search_ranked_targets` for specific keywords.\n"
        "3. **INSPECT:** Use `inspect_fqn` to get exact signatures and docstrings. THIS IS CRITICAL.\n"
        "4. **SAVE:** Call `save_knowledge(summary)` with a detailed summary of findings.\n"
        "5. **STOP:** Just stop generating tools when done (or run out of turns).\n"
    )

    if is_coding:
        instruction += (
            "\n**ITERATIVE MODE:** You are part of a coding loop. "
            "Review the `analysis_feedback` below. If there is a `AttributeError` or `ImportError`, "
            "specifically search for the correct name of that attribute/class.\n"
            "Feedback: {analysis_feedback}\n"
            "Plan: {implementation_plan}\n"
        )
    else:
        instruction += "Request: {user_request}"

    worker = LlmAgent(
        name="retrieval_worker",
        model=model,
        tools=[
            FunctionTool(list_ranked_targets),
            FunctionTool(search_ranked_targets),
            FunctionTool(inspect_fqn),
            FunctionTool(save_knowledge),
            # FunctionTool(exit_loop) # REMOVED to prevent killing outer loop
        ],
        include_contents="default",
        instruction=instruction,
    )

    return LoopAgent(
        name="retrieval_loop",
        sub_agents=[worker],
        max_iterations=2,  # Hard limit to force return to outer loop
    )


def _create_interactive_retrieval_agent(tools_helper: AdkTools, model) -> Agent:
    """
    Creates an INTERACTIVE Retrieval Agent (V46 style).
    Used by Knowledge Expert. Writes directly to history (no Loop wrapper).
    """

    def save_selected_seeds(seeds: list[str], tool_context: ToolContext) -> str:
        """Saves the selected seeds and marks retrieval as complete."""
        # We don't really need the seeds in state, but the tool helps the agent signal completion.
        tool_context.session.state["relevant_modules_json"] = json.dumps(
            {"modules": seeds}
        )
        return f"Seeds saved: {seeds}. Retrieval complete."

    async def list_ranked_targets(
        page: int = 1, tool_context: ToolContext = None
    ) -> str:
        return tools_helper.list_ranked_targets(page=page)

    async def inspect_fqn(fqn: str, tool_context: ToolContext) -> str:
        return tools_helper.inspect_ranked_target(fqn)

    async def search_ranked_targets(
        query: str | list[str], page: int = 1, tool_context: ToolContext = None
    ) -> str:
        return tools_helper.search_ranked_targets(query, page=page)

    return LlmAgent(
        name="knowledge_retrieval_agent",
        model=model,
        tools=[
            FunctionTool(list_ranked_targets),
            FunctionTool(search_ranked_targets),
            FunctionTool(inspect_fqn),
            FunctionTool(save_selected_seeds),
        ],
        include_contents="default",  # CRITICAL: Writes to history for Solver
        instruction=(
            "You are the Hierarchical Retrieval Agent. Your goal is to find relevant ADK classes/methods.\n"
            "**STRATEGY:**\n"
            "- **BROWSE FIRST:** ALWAYS call `list_ranked_targets(page=1)` first.\n"
            "- **Then Search:** Use `search_ranked_targets` if needed.\n"
            "- **Inspect Everything:** Use `inspect_fqn` to see exact field names and docstrings.\n"
            "- **Finalize:** Call `save_selected_seeds` when you have found the info needed to answer.\n"
            "Request: {user_request}"
        ),
    )


# --- Knowledge Expert Components ---


class SharedHistorySolver(LlmAgent):
    """Answers using Shared History (V46 style)."""

    def __init__(self, model, **kwargs):
        super().__init__(
            name="single_step_solver",
            model=model,
            tools=[],
            include_contents="default",  # CRITICAL: Sees Retrieval history
            output_key="final_response",
            instruction=(
                "You are the ADK Expert Solver.\n"
                "**REQUEST:** {user_request}\n\n"
                "**GOAL:**\n"
                "Review the conversation history above (retrieval steps). Answer the request.\n"
                "1. **Coding Tasks:** Implement EXACTLY what is asked. Use the retrieved API signatures.\n"
                "2. **API Questions:** Identify the Fully Qualified Name (FQN) and provide the exact import path.\n"
                "3. **Multiple Choice:** Evaluate the options against the retrieved docstrings.\n"
                "Output a detailed, natural language response."
            ),
            **kwargs,
        )


def _create_knowledge_expert(tools_helper: AdkTools, model) -> Agent:
    """Combines interactive retrieval and shared-history solver."""
    retrieval = _create_interactive_retrieval_agent(tools_helper, model)
    solver = SharedHistorySolver(model=model)
    return SequentialAgent(name="knowledge_expert", sub_agents=[retrieval, solver])


# --- Coding Expert Components ---


def _create_coding_expert(tools_helper: AdkTools, model) -> Agent:
    """Implements the V29 coding loop with ISOLATED retrieval."""

    initial_retrieval = _create_isolated_retrieval_loop(
        tools_helper, model, is_coding=False
    )
    loop_retrieval = _create_isolated_retrieval_loop(
        tools_helper, model, is_coding=True
    )

    planner = LlmAgent(
        name="implementation_planner",
        model=model,
        include_contents="none",
        output_key="implementation_plan",
        instruction=(
            "You are the Implementation Planner. "
            "Request: {user_request}\n"
            "Context: {knowledge_context}\n"
            "Plan a step-by-step implementation. Output natural text."
        ),
    )

    verification_planner = LlmAgent(
        name="verification_planner",
        model=model,
        include_contents="none",
        output_key="verification_plan",
        output_schema=VerificationPlan,
        instruction=(
            "You are the Verification Planner. "
            "Request: {user_request}\n"
            "Plan: {implementation_plan}\n"
            "Formulate a COMPREHENSIVE verification plan consisting of multiple test cases. "
            "Each test case must target a specific requirement from the request. "
            "Ensure the test prompts are something the agent being built can actually handle."
        ),
    )

    candidate_creator = LlmAgent(
        name="candidate_creator",
        model=model,
        tools=[
            FunctionTool(tools_helper.read_file),
            FunctionTool(tools_helper.write_file),
            FunctionTool(tools_helper.replace_text),
        ],
        output_key="candidate_response",
        include_contents="none",
        instruction=(
            "You are the Candidate Creator. "
            "Plan: {implementation_plan}\n"
            "Context: {knowledge_context}\n"
            "Feedback: {analysis_feedback}\n"
            "Implement code based on Context/Plan. Output rationale + code block."
        ),
    )

    runner = CodeBasedRunner(
        name="code_based_runner",
        tools_helper=tools_helper,
        model_name=model.model if hasattr(model, "model") else model,
    )

    analyst = LlmAgent(
        name="run_analyst",
        model=model,
        tools=[FunctionTool(exit_loop)],
        include_contents="none",
        output_key="analysis_feedback",
        instruction=(
            "You are the Run Analyst. "
            "Verification Plan: {verification_plan}\n"
            "Combined Logs: {run_output}\n"
            "Analyze the output of ALL test cases against the expected behavior. "
            "If all tests passed, call `exit_loop`. "
            "If any test failed, diagnose the issue and provide feedback for the creator."
        ),
    )

    loop = LoopAgent(
        name="implementation_loop",
        sub_agents=[loop_retrieval, candidate_creator, runner, analyst],
        max_iterations=3,
    )

    final_verifier = CodeBasedFinalVerifier(
        name="final_verifier", tools_helper=tools_helper
    )

    return SequentialAgent(
        name="coding_expert",
        sub_agents=[
            initial_retrieval,
            planner,
            verification_planner,
            loop,
            final_verifier,
        ],
    )


# --- Router ---


class RoutingDelegator(Agent):
    """Routes to Coding or Knowledge expert."""

    def __init__(self, model, coding_expert: Agent, knowledge_expert: Agent, **kwargs):
        super().__init__(**kwargs)
        self._coding_expert = coding_expert
        self._knowledge_expert = knowledge_expert

        def route_task(category: str, tool_context: ToolContext) -> str:
            tool_context.session.state["route_category"] = category
            return f"Routed to {category}"

        self._router = LlmAgent(
            name="router",
            model=model,
            tools=[FunctionTool(route_task)],
            include_contents="none",
            instruction=(
                "You are the Request Router. Your ONLY task is to classify the user request.\n"
                "1. CODING: User wants to implement an agent, fix code, or write scripts.\n"
                "2. KNOWLEDGE: User asks a question about ADK, multiple choice, or API definitions.\n\n"
                "**STRICT RULE:** You MUST call `route_task` with 'CODING' or 'KNOWLEDGE'.\n"
                "Do NOT provide reasoning, do NOT attempt to solve the request, and do NOT output any other text."
            ),
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        route_decision = ctx.session.state.get("route_category")
        if not route_decision:
            async for event in self._router.run_async(ctx):
                yield event
            route_decision = ctx.session.state.get("route_category", "KNOWLEDGE")

        target = (
            self._coding_expert
            if "CODING" in route_decision.upper()
            else self._knowledge_expert
        )

        result_text = ""
        async for event in target.run_async(ctx):
            yield event
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        result_text = part.text

        ctx.session.state["final_response"] = result_text


# --- Factory ---


def create_hybrid_generator_v47(
    model_name: str, api_key_manager: ApiKeyManager = None, adk_branch="v1.20.0"
) -> AdkAnswerGenerator:

    name_prefix = "ADK_HYBRID_V47"
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_v47_"))
    setup_hook = create_standard_setup_hook(workspace_root, adk_branch, name_prefix)
    tools_helper = AdkTools(workspace_root, venv_path=workspace_root / "venv")
    gemini_client = RotatingKeyGemini(model=model_name, api_key_manager=api_key_manager)

    # Experts
    knowledge_expert = _create_knowledge_expert(tools_helper, gemini_client)
    coding_expert = _create_coding_expert(tools_helper, gemini_client)

    # Router
    router = RoutingDelegator(
        name="routing_delegator",
        model=gemini_client,
        knowledge_expert=knowledge_expert,
        coding_expert=coding_expert,
    )

    # Pipeline
    setup = SetupAgentCodeBased(
        name="setup", workspace_root=workspace_root, tools_helper=tools_helper
    )
    teardown = CodeBasedTeardownAgent(
        name="teardown", workspace_root=workspace_root, tools_helper=tools_helper
    )

    agent = SequentialAgent(name="adk_v47", sub_agents=[setup, router, teardown])

    return PostProcessedAdkAnswerGenerator(
        model_client=gemini_client,
        workspace_root=workspace_root,
        agent=agent,
        name=f"{name_prefix}",
        setup_hook=setup_hook,
        api_key_manager=api_key_manager,
        model_name=model_name,
    )
