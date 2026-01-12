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

"""ADK Agents for Prismatic Evaluation."""

import asyncio
from typing import Optional
from pydantic import PrivateAttr

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent, InvocationContext, Agent
from google.adk.tools import FunctionTool, exit_loop
from google.genai import types
from google.adk.events import Event, EventActions

from benchmarks.benchmark_generator.tools import (
    trace_execution, validate_mutant, save_benchmark_case, 
    check_uniqueness, scan_repository, list_prioritized_targets, select_target
)
from benchmarks.benchmark_generator.models import TargetEntity, TargetType, ObserverOutput, SaboteurOutput
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.answer_generators.adk_agents import RotatingKeyGemini
from benchmarks.api_key_manager import ApiKeyManager

class SemaphoreGemini(RotatingKeyGemini):
    """A Gemini model that limits concurrency using a semaphore and retries on 429."""
    _semaphore: asyncio.Semaphore = PrivateAttr()

    def __init__(self, semaphore: asyncio.Semaphore, **kwargs):
        super().__init__(**kwargs)
        self._semaphore = semaphore

    async def generate_content_async(self, *args, **kwargs):
        """Wraps the generation with a semaphore and retry logic."""
        # The semaphore is entered when the generator is started (iterated)
        async with self._semaphore:
            max_retries = 5
            attempt = 0
            while attempt <= max_retries:
                try:
                    # Call super method
                    result = super(SemaphoreGemini, self).generate_content_async(*args, **kwargs)
                    
                    # If it returns a coroutine (non-streaming response), await it
                    if asyncio.iscoroutine(result):
                        result = await result
                    
                    # If result is iterable (streaming), yield chunks
                    if hasattr(result, '__aiter__'):
                        async for item in result:
                            yield item
                    else:
                        # Otherwise yield the single result
                        yield result
                    return # Success, exit loop

                except Exception as e:
                    # Simple retry logic for 429
                    is_429 = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                    if is_429 and attempt < max_retries:
                        attempt += 1
                        await asyncio.sleep(2 * attempt)
                        continue
                    else:
                        raise e

# --- Agents ---

def create_observer_agent(model: str | RotatingKeyGemini) -> LlmAgent:
    """Creates the Observer agent responsible for generating ground truth code."""
    return LlmAgent(
        name="Observer",
        model=model,
        tools=[FunctionTool(trace_execution)],
        include_contents='none',
        output_key="observer_status",
        output_schema=ObserverOutput,
        instruction=(
            "You are the Observer (The Developer). Your goal is to create a realistic, VALID usage example for the selected TargetEntity.\n"
            "\n=== TARGET CONTEXT ===\n"
            "{current_target_json}\n"
            "======================\n"
            "1. Analyze the `current_target_json` provided above. It contains the target's SOURCE CODE.\n"
            "2. Incorporate the `associated_context` (related modules/classes) to build an INTEGRATION test case, not an isolated unit test.\n"
            "3. Call `trace_execution` with `code` (the Python script) and `target_method` (the dictionary from `current_target_json`).\n"
            "4. CRITICAL: Agents should use real constructors/stubs (like StubAgent) where necessary. NEVER use MagicMock.\n"
            "5. After verification, YOU MUST OUTPUT VALID JSON matching the ObserverOutput schema. Do not output markdown code blocks around the JSON.\n"
            "   Example: {\"status\": \"success\", \"rationale\": \"Tested via stubs\", \"code_generated\": \"...\"}"
        )
    )

def create_saboteur_agent(model: str | RotatingKeyGemini) -> LlmAgent:
    """Creates the Saboteur agent responsible for generating adversarial mutants."""
    return LlmAgent(
        name="Saboteur",
        model=model,
        tools=[], 
        include_contents='none',
        output_key="saboteur_output",
        output_schema=SaboteurOutput,
        instruction=(
            "You are the Saboteur. Your goal is to create 3 valid distractors (Hard Negatives)."
            "\nGolden Snapshot: {current_snapshot}"
            "Previous Feedback (if any): {saboteur_feedback}"
            "CRITICAL: Do NOT use `unittest.mock.MagicMock`. "
            "1. Generate 3 distinct mutants of the valid code (Semantic, Poisoning, Structure)."
            "   - If there is feedback, FIX the issues mentioned."
            "2. Output a structured SaboteurOutput containing the list of mutants."
        )
    )

def create_referee_agent(model: str | RotatingKeyGemini) -> LlmAgent:
    """Creates the Referee agent responsible for validating mutants."""
    return LlmAgent(
        name="Referee",
        model=model,
        tools=[FunctionTool(validate_mutant), FunctionTool(exit_loop)],
        include_contents='none',
        output_key="saboteur_feedback",
        instruction=(
            "You are the Referee. Validate the mutants produced by the Saboteur."
            "\nMutants (Saboteur Output): {saboteur_output}"
            "CRITICAL: NEVER suggest using `MagicMock`. "
            "1. Iterate through the mutants in the output."
            "2. For EACH mutant, call `validate_mutant`."
            "3. Analyze results:"
            "   - If ALL 3 mutants are VALID, call `exit_loop` to finish the Adversarial Phase."
            "   - If ANY mutant is invalid, construct constructive feedback for the Saboteur."
        )
    )

def create_critic_agent(model: str | RotatingKeyGemini) -> LlmAgent:
    """Creates the Critic agent responsible for deduplication."""
    return LlmAgent(
        name="Critic",
        model=model,
        tools=[FunctionTool(check_uniqueness)],
        include_contents='none',
        output_key="critic_verdict",
        instruction=(
            "You are the Critic. Ensure the benchmark is unique."
            "\nProposed Question Context: {current_target_json}"
            "1. Formulate a draft question string based on the target."
            "2. Call `check_uniqueness(question_text=...)`."
            "3. If unique, output 'APPROVED'."
            "4. If not unique, output 'REJECTED'."
        )
    )

def create_assembler_agent(model: str | RotatingKeyGemini) -> LlmAgent:
    """Creates the Assembler agent responsible for formatting the final benchmark case."""
    return LlmAgent(
        name="Assembler",
        model=model,
        tools=[FunctionTool(save_benchmark_case)],
        include_contents='none',
        output_key="assembler_status",
        instruction=(
            "You are the Assembler."
            "\nCritic Verdict: {critic_verdict}"
            "Target: {current_target_json}"
            "Snapshot: {current_snapshot}"
            "Mutants: {saboteur_output}"
            "1. If Critic Verdict is 'REJECTED', do nothing and output 'SKIPPED'."
            "2. Otherwise, formulate the final Multiple Choice Question."
            "3. CRITICAL: Do not output the JSON as text. You MUST call `save_benchmark_case` with the JSON string."
            "4. Output 'SAVED'."
        )
    )

def create_worker_pipeline(model_name: str = "gemini-3-pro-preview", api_key_manager: Optional[ApiKeyManager] = None, concurrency: int = 1) -> Agent:
    """Creates the stateless worker pipeline for processing a single target."""
    
    if api_key_manager:
        semaphore = asyncio.Semaphore(concurrency)
        model = SemaphoreGemini(model=model_name, api_key_manager=api_key_manager, semaphore=semaphore)
    else:
        model = model_name

    observer = create_observer_agent(model)
    saboteur = create_saboteur_agent(model)
    referee = create_referee_agent(model)
    
    # Adversarial loop tries to fix mutants up to 3 times
    adversarial_loop = LoopAgent(
        name="AdversarialLoop",
        sub_agents=[saboteur, referee],
        max_iterations=3
    )
    
    critic = create_critic_agent(model)
    assembler = create_assembler_agent(model)
    
    # Linear sequence: Observer -> (Saboteur <-> Referee) -> Critic -> Assembler
    return SequentialAgent(
        name="BenchmarkWorker",
        sub_agents=[observer, adversarial_loop, critic, assembler]
    )

def create_prismatic_agent(model_name: str = "gemini-3-pro-preview", api_key_manager: Optional[ApiKeyManager] = None, repo_path: str = ".", concurrency: int = 1) -> Agent:
    """
    Creates the top-level Prismatic Agent that orchestrates the entire generation process.
    It includes an 'Auditor' (Coordinator) that manages the target queue and a 'Worker' pipeline.
    """
    
    # The Coordinator (Auditor)
    # It uses a cheaper model or just tools since it's mostly deterministic logic via tools?
    # Actually, the instructions say "Auditor uses scan_repository".
    # But here we can just use a simple tool-using agent.
    
    # We reuse the same model logic for Auditor (or a simpler one if desired, but consistency is safer)
    if api_key_manager:
        semaphore = asyncio.Semaphore(concurrency)
        auditor_model = SemaphoreGemini(model=model_name, api_key_manager=api_key_manager, semaphore=semaphore)
    else:
        auditor_model = model_name
        
    auditor = LlmAgent(
        name="Auditor",
        model=auditor_model,
        tools=[FunctionTool(scan_repository), FunctionTool(list_prioritized_targets), FunctionTool(select_target)],
        include_contents='none',
        instruction=(
            f"You are the Auditor (Coordinator). Your goal is to select the next high-value target for benchmarking from '{repo_path}'.\n"
            "1. If targets are not scanned, call `scan_repository(repo_path='{repo_path}')`."
            "2. Call `list_prioritized_targets()` to see the queue."
            "3. Select the highest priority target (top of list) using `select_target(target_id=...)`."
            "4. Output 'TARGET_SELECTED' to hand off to the Worker."
        )
    )

    worker = create_worker_pipeline(model_name, api_key_manager, concurrency)

    return SequentialAgent(
        name="PrismaticRunner",
        sub_agents=[auditor, worker]
    )