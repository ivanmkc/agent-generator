"""
Agent definitions for the Benchmark Generator.

This module assembles the multi-agent system used to generate benchmarks.
It defines the roles:
- Auditor: Selects targets.
- Observer: Traces execution.
- Saboteur: Creates distractors.
- Architect: Assembles the final MCQ.
"""

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ADK Agents for Agentic Evaluation."""

import asyncio
import logging
import time
from typing import Optional
from pydantic import PrivateAttr

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent, InvocationContext, Agent
from google.adk.tools import FunctionTool, exit_loop
from google.genai import types
from google.adk.events import Event, EventActions

from benchmarks.generator.benchmark_generator.agent_tools import (
    trace_execution,
    validate_mutant,
    save_benchmark_case,
    check_uniqueness,
    scan_repository,
    list_prioritized_targets,
    select_target,
    assemble_and_save_benchmark,
)
from benchmarks.generator.benchmark_generator.models import TargetEntity, TargetType, ObserverOutput, SaboteurOutput
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.answer_generators.adk_agents import RotatingKeyGemini
from core.api_key_manager import ApiKeyManager

# Setup logger for agents
logger = logging.getLogger(__name__)


class SemaphoreGemini(RotatingKeyGemini):
    """A Gemini model that limits concurrency using a semaphore and retries on 429."""

    _semaphore: asyncio.Semaphore = PrivateAttr()
    _model_name_log: str = PrivateAttr()

    def __init__(self, semaphore: asyncio.Semaphore, **kwargs):
        super().__init__(**kwargs)
        self._semaphore = semaphore
        # Extract model name for logging
        self._model_name_log = kwargs.get("model", "unknown_model")

    async def generate_content_async(self, *args, **kwargs):
        """Wraps the generation with a semaphore and retry logic."""
        # The semaphore is entered when the generator is started (iterated)
        async with self._semaphore:
            max_retries = 5
            attempt = 0
            while attempt <= max_retries:
                try:
                    t0 = time.time()
                    # Call super method
                    result = super(SemaphoreGemini, self).generate_content_async(
                        *args, **kwargs
                    )

                    # If it returns a coroutine (non-streaming response), await it
                    if asyncio.iscoroutine(result):
                        result = await result

                    # If result is iterable (streaming), yield chunks
                    if hasattr(result, "__aiter__"):
                        async for item in result:
                            yield item
                    else:
                        # Otherwise yield the single result
                        yield result

                    dt = time.time() - t0
                    logger.info(f"[{self._model_name_log}] Generation took {dt:.2f}s")

                    return  # Success, exit loop

                except Exception as e:
                    # Retry logic for Rate Limit (429) and Server Errors (500, 502, 503, 504)
                    error_str = str(e)
                    is_retryable = (
                        "429" in error_str
                        or "RESOURCE_EXHAUSTED" in error_str
                        or "500" in error_str
                        or "502" in error_str
                        or "503" in error_str
                        or "504" in error_str
                        or "UNAVAILABLE" in error_str
                        or "overloaded" in error_str
                    )

                    if is_retryable and attempt < max_retries:
                        attempt += 1
                        logger.warning(
                            f"Retryable error ({e}). Retrying attempt {attempt}/{max_retries} in {2 * attempt}s..."
                        )
                        await asyncio.sleep(2 * attempt)
                        continue
                    else:
                        logger.error(f"Generation failed after {attempt} attempts: {e}")
                        raise e


# --- Agents ---


def create_observer_agent(model: str | RotatingKeyGemini) -> LlmAgent:
    """Creates the Observer agent responsible for generating ground truth code."""
    return LlmAgent(
        name="Observer",
        model=model,
        tools=[FunctionTool(trace_execution)],
        include_contents="none",
        # No output_key, we rely on the tool call side-effect
        instruction=(
            "You are the Observer. Your SOLE purpose is to execute the 'trace_execution' tool.\n"
            "\n=== TARGET ===\n"
            "{current_target_json}\n"
            "\n=== INSTRUCTIONS ===\n"
            "1. Write a Python script that validly uses the target entity.\n"
            "2. CALL `trace_execution(code=..., target_method=...)` immediately.\n"
            "3. If the tool result is 'success', output 'DONE'.\n"
            "4. If 'error', fix the code and retry.\n"
        ),
    )


def create_saboteur_agent(model: str | RotatingKeyGemini) -> LlmAgent:
    """Creates the Saboteur agent responsible for generating adversarial mutants."""
    return LlmAgent(
        name="Saboteur",
        model=model,
        tools=[],
        include_contents="none",
        output_key="saboteur_output",
        instruction=(
            "You are the Saboteur. Your goal is to create 3 valid distractors (Hard Negatives)."
            "\nGolden Snapshot: {current_snapshot}"
            "Previous Feedback (if any): {saboteur_feedback}"
            "CRITICAL: Do NOT use `unittest.mock.MagicMock`. "
            "1. Generate 3 distinct mutants of the valid code (Semantic, Poisoning, Structure)."
            "   - If there is feedback, FIX the issues mentioned."
            "2. Output a structured JSON containing a 'mutants' list. Each mutant must have: code, mutation_type, mutation_description, diff_from_golden."
        ),
    )


def create_referee_agent(model: str | RotatingKeyGemini) -> LlmAgent:
    """Creates the Referee agent responsible for validating mutants."""
    return LlmAgent(
        name="Referee",
        model=model,
        tools=[FunctionTool(validate_mutant), FunctionTool(exit_loop)],
        include_contents="none",
        output_key="saboteur_feedback",
        instruction=(
            "You are the Referee. Validate the mutants produced by the Saboteur."
            "\nMutants (Saboteur Output): {saboteur_output}"
            "CRITICAL: NEVER suggest using `MagicMock`. "
            "1. Iterate through the mutants in the output."
            "2. For EACH mutant, call `validate_mutant` with the mutant's code."
            "3. Analyze results:"
            "   - If ALL 3 mutants are VALID (Divergent Output or Runtime Crash), call `exit_loop` to finish the Adversarial Phase."
            "   - If ANY mutant is invalid (Equivalent Mutant), provide constructive feedback to the Saboteur."
        ),
    )


def create_critic_agent(model: str | RotatingKeyGemini) -> LlmAgent:
    """Creates the Critic agent responsible for deduplication."""
    return LlmAgent(
        name="Critic",
        model=model,
        tools=[FunctionTool(check_uniqueness)],
        include_contents="none",
        output_key="critic_verdict",
        instruction=(
            "You are the Critic. Ensure the benchmark is unique."
            "\nContext: {current_target_json}"
            "\nAnalyst Output (if any): {analyst_output}"
            "1. Formulate a draft question string based on the target name and responsibility."
            "2. Call `check_uniqueness(question_text=...)`."
            "3. If unique (score < 0.8), output 'APPROVED'."
            "4. If not unique, output 'REJECTED'."
        ),
    )


def create_assembler_agent(
    model: str | RotatingKeyGemini, mode: str = "execution_mcq"
) -> LlmAgent:
    """Creates the Assembler agent responsible for formatting the final benchmark case."""

    if mode == "execution_mcq":
        instruction = (
            "You are the Assembler. Your goal is to construct the Explanation for the Multiple Choice Question.\n"
            "\n=== INPUTS ===\n"
            "1. Golden Snapshot (Correct Answer): {current_snapshot}\n"
            "2. Distractors (Saboteur Output): {saboteur_output}\n"
            "3. Critic Verdict: {critic_verdict}\n"
            "\n=== INSTRUCTIONS ===\n"
            "1. If Critic Verdict is 'REJECTED', output 'SKIPPED'.\n"
            "2. Analyze why the Distractors (Options B, C, D) are incorrect compared to the Golden Snapshot (Option A).\n"
            "3. Write a clear, concise `explanation` string.\n"
            "4. MANDATORY: Call `assemble_and_save_benchmark(explanation='...')` with your explanation.\n"
            "   - DO NOT generate the JSON yourself. The tool will assemble the code snippets programmatically.\n"
            "5. Output 'SAVED'."
        )
        tools = [FunctionTool(assemble_and_save_benchmark)]
    else:  # concept_mcq
        instruction = (
            "You are the Assembler. Your goal is to construct a **CONCEPTUAL** Multiple Choice Question.\n"
            "\n=== INPUTS ===\n"
            "1. Concept Analysis (Correct Answer): {analyst_output}\n"
            "2. Distractors (Confabulator Output): {confabulator_output}\n"
            "3. Reviewer Verdict: {reviewer_verdict}\n"
            "4. Critic Verdict: {critic_verdict}\n"
            "5. Target Metadata: {current_target_json}\n"
            "\n=== INSTRUCTIONS ===\n"
            "1. If Reviewer Verdict is 'REJECTED' OR Critic Verdict is 'REJECTED', output 'SKIPPED'.\n"
            "2. Construct the options (A, B, C, D) as **TEXT DESCRIPTIONS**.\n"
            "   - One option must be the core responsibility identified by the Analyst.\n"
            "   - Three options must be the plausible but incorrect descriptions from the Confabulator.\n"
            "3. **CRITICAL: The Question text MUST explicitly name the target function or class EXACTLY as it appears in the metadata.**\n"
            "   - BAD: 'What is the responsibility of this function?'\n"
            "   - BAD: 'What is the responsibility of the forecast_timesfm function?' (Do not combine function name with model name!)\n"
            "   - GOOD: 'What is the primary responsibility of the `get_fast_api_app` function?'\n"
            "   - Extract the name directly from `current_target_json`['name'].\n"
            "4. Call `save_benchmark_case(question='...', options={'A': '...', ...}, correct_answer='A', explanation='...')`.\n"
            "5. Output 'SAVED'."
        )
        tools = [FunctionTool(save_benchmark_case)]

    return LlmAgent(
        name="Assembler",
        model=model,
        tools=tools,
        include_contents="none",
        output_key="assembler_status",
        instruction=instruction,
    )


def create_concept_worker(model: str | RotatingKeyGemini) -> Agent:
    """Creates the worker pipeline for Conceptual MCQs."""

    analyst = LlmAgent(
        name="Analyst",
        model=model,
        include_contents="none",
        output_key="analyst_output",
        instruction=(
            "You are the Analyst. Your goal is to identify the PRIMARY RESPONSIBILITY of the target.\n"
            "\n=== TARGET ===\n"
            "{current_target_json}\n"
            "\n=== INSTRUCTIONS ===\n"
            "1. Read the docstring and source code in `current_target_json`.\n"
            "2. Summarize the single most important responsibility of this class/function in 1-2 sentences.\n"
            "3. Extract 2-3 key constraints or details that distinguish it from similar components.\n"
            "4. Output this summary clearly."
        ),
    )

    confabulator = LlmAgent(
        name="Confabulator",
        model=model,
        include_contents="none",
        output_key="confabulator_output",
        instruction=(
            "You are the Confabulator. Your goal is to generate 3 Plausible but INCORRECT descriptions (Distractors).\n"
            "\n=== TRUTH ===\n"
            "{analyst_output}\n"
            "\n=== INSTRUCTIONS ===\n"
            "1. Generate 3 distinct distractors based on:\n"
            "   - **Hallucination:** Attribute functionality that belongs to a different ADK component.\n"
            "   - **Over-simplification:** Describe it as doing much less than it does.\n"
            "   - **Exaggeration:** Describe it as doing things it doesn't (e.g., 'Runner manages database migrations').\n"
            "2. Ensure they sound technical and plausible to a junior engineer.\n"
            "3. Output ONLY the 3 distractors as a numbered list."
        ),
    )

    reviewer = LlmAgent(
        name="Reviewer",
        model=model,
        include_contents="none",
        output_key="reviewer_verdict",
        instruction=(
            "You are the Reviewer. Validate the distractors.\n"
            "\n=== TRUTH ===\n"
            "{analyst_output}\n"
            "\n=== DISTRACTORS ===\n"
            "{confabulator_output}\n"
            "\n=== INSTRUCTIONS ===\n"
            "1. Check if any distractor is accidentally correct or too vague.\n"
            "2. If all 3 are clearly distinguishable from the Truth, output 'APPROVED'.\n"
            "3. If any are ambiguous, output 'REJECTED' and explain why."
        ),
    )

    critic = create_critic_agent(model)
    assembler = create_assembler_agent(model, mode="concept_mcq")

    return SequentialAgent(
        name="ConceptWorker",
        sub_agents=[analyst, confabulator, reviewer, critic, assembler],
    )


def create_worker_pipeline(model: str | RotatingKeyGemini, mode: str) -> Agent:
    """Creates the stateless worker pipeline for processing a single target."""

    if mode == "concept_mcq":

        return create_concept_worker(model)

    # Default to execution_mcq

    observer = create_observer_agent(model)

    saboteur = create_saboteur_agent(model)

    referee = create_referee_agent(model)

    # Adversarial loop tries to fix mutants up to 3 times

    adversarial_loop = LoopAgent(
        name="AdversarialLoop", sub_agents=[saboteur, referee], max_iterations=3
    )

    critic = create_critic_agent(model)

    assembler = create_assembler_agent(model, mode="execution_mcq")

    return SequentialAgent(
        name="BenchmarkWorker",
        sub_agents=[observer, adversarial_loop, critic, assembler],
    )


def create_agentic_agent(
    model: str | RotatingKeyGemini,
    auditor_model: str | RotatingKeyGemini,
    repo_path: str,
    mode: str,
) -> Agent:
    """

    Creates the top-level Agentic Agent that orchestrates the entire generation process.

    It includes an 'Auditor' (Coordinator) that manages the target queue and a 'Worker' pipeline.

    """

    auditor = LlmAgent(
        name="Auditor",
        model=auditor_model,
        tools=[
            FunctionTool(scan_repository),
            FunctionTool(list_prioritized_targets),
            FunctionTool(select_target),
            FunctionTool(exit_loop),
        ],
        include_contents="none",
        instruction=(
            f"You are the Auditor (Coordinator). Your goal is to select the next high-value target for benchmarking from '{repo_path}'.\n"
            "1. If targets are not scanned, call `scan_repository(repo_path='{repo_path}')`."
            "2. Call `list_prioritized_targets()` to see the queue."
            "3. Select the highest priority target (top of list) using `select_target(target_id=...)`."
            "4. Output 'TARGET_SELECTED' to hand off to the Worker."
        ),
    )

    worker = create_worker_pipeline(model, mode)

    return SequentialAgent(name="AgenticRunner", sub_agents=[auditor, worker])
