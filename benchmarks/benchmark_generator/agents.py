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
from google.adk.events import Event

from benchmarks.benchmark_generator.tools import (
    scan_repository, trace_execution, validate_mutant, save_benchmark_case, get_prioritized_target, check_uniqueness
)
from benchmarks.benchmark_generator.models import TargetMethod, ObserverOutput, SaboteurOutput
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.answer_generators.adk_agents import RotatingKeyGemini
from benchmarks.api_key_manager import ApiKeyManager

class SemaphoreGemini(RotatingKeyGemini):
    """A Gemini model that limits concurrency using a semaphore."""
    _semaphore: asyncio.Semaphore = PrivateAttr()

    def __init__(self, semaphore: asyncio.Semaphore, **kwargs):
        super().__init__(**kwargs)
        self._semaphore = semaphore

    def generate_content_async(self, *args, **kwargs):
        # Must return an async generator, not a coroutine, to satisfy Aclosing
        async def _throttled_generator():
            max_retries = 3
            attempt = 0
            while True:
                try:
                    async with self._semaphore:
                        # super().generate_content_async is a regular function returning an awaitable or generator
                        result = super(SemaphoreGemini, self).generate_content_async(*args, **kwargs)
                        
                        if asyncio.iscoroutine(result):
                            result = await result
                        
                        if hasattr(result, '__aiter__'):
                            async for item in result:
                                yield item
                        else:
                            yield result
                        return # Success
                except Exception as e:
                    is_429 = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                    if is_429 and attempt < max_retries:
                        attempt += 1
                        print(f"Hit 429. Rotating key and retrying (Attempt {attempt}/{max_retries})...")
                        await asyncio.sleep(2 * attempt)
                        continue
                    else:
                        raise e
        
        return _throttled_generator()

# --- Agents ---

def create_auditor_agent(model: str | RotatingKeyGemini, repo_path: str) -> LlmAgent:
    """Creates the Auditor agent responsible for selecting benchmark targets."""
    return LlmAgent(
        name="Auditor",
        model=model,
        tools=[FunctionTool(scan_repository), FunctionTool(get_prioritized_target), FunctionTool(exit_loop)],
        include_contents='none', # State-based
        output_key="current_target_json",
        output_schema=TargetMethod,
        instruction=(
            f"You are the Auditor (The Strategist). Your goal is to map the repository's topology and select high-value targets based on USAGE frequency.\n"
            f"1. If 'scanned_targets' is empty, call `scan_repository` with `repo_path='{repo_path}'`.\n"
            "2. Call `get_prioritized_target` to retrieve the next best target (prioritized by Usage Count, IRT, and Coverage).\n"
            "3. Analyze the target's usage patterns. If it has high usage, it is a critical API surface.\n"
            "4. If it returns 'DONE' or 'EMPTY', call `exit_loop`.\n"
            "5. Otherwise, output the target strictly adhering to the TargetMethod schema."
        )
    )

def create_observer_agent(model: str | RotatingKeyGemini) -> LlmAgent:
    """Creates the Observer agent responsible for generating ground truth code."""
    # Observer uses a tool to perform the action. Output schema might conflict if tool calling is primary.
    # However, we can use output_schema to force a structured status report AFTER the tool call.
    return LlmAgent(
        name="Observer",
        model=model,
        tools=[FunctionTool(trace_execution)],
        include_contents='none',
        output_key="observer_status",
        output_schema=ObserverOutput,
        instruction=(
            "You are the Observer. Your goal is to generate a VALID usage example for the target method.\n"
            "Target Method Metadata: {current_target_json}\n"
            "CRITICAL: Do NOT use `unittest.mock.MagicMock` or similar mocking libraries. "
            "Pydantic-based components in the target repo fail to validate mock objects. "
            "Instead, use real constructors with minimal valid arguments or define simple concrete stub classes.\n"
            "1. Analyze the target method.\n"
            "2. Call `trace_execution` with two arguments:\n"
            "   - `code`: a self-contained Python script that imports and calls this method correctly without using mocks.\n"
            "   - `target_method`: The EXACT dictionary provided in `{current_target_json}`.\n"
            "3. After the tool call, output a structured ObserverOutput indicating success or failure."
        )
    )

def create_saboteur_agent(model: str | RotatingKeyGemini) -> LlmAgent:
    """Creates the Saboteur agent responsible for generating adversarial mutants."""
    return LlmAgent(
        name="Saboteur",
        model=model,
        tools=[], # No tools, purely generative now. Validation is done by Referee.
        include_contents='none',
        output_key="saboteur_output",
        output_schema=SaboteurOutput,
        instruction=(
            "You are the Saboteur. Your goal is to create 3 valid distractors (Hard Negatives).\n"
            "Golden Snapshot: {current_snapshot}\n"
            "Previous Feedback (if any): {saboteur_feedback}\n"
            "CRITICAL: Do NOT use `unittest.mock.MagicMock`. Use real objects or simple concrete stubs.\n"
            "1. Generate 3 distinct mutants of the valid code (Semantic, Poisoning, Structure).\n"
            "   - If there is feedback, FIX the issues mentioned (e.g. fix syntax error, make it diverge if equivalent).\n"
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
            "You are the Referee. Validate the mutants produced by the Saboteur.\n"
            "Mutants (Saboteur Output): {saboteur_output}\n"
            "CRITICAL: When providing feedback, NEVER suggest using `MagicMock`. "
            "Suggest using real class constructors or defining minimal concrete stub classes instead.\n"
            "1. Iterate through the mutants in the output.\n"
            "2. For EACH mutant, call `validate_mutant`.\n"
            "3. Analyze results:\n"
            "   - If ALL 3 mutants are VALID (divergent output, no unexpected crashes unless intended), call `exit_loop` to finish the Adversarial Phase.\n"
            "   - If ANY mutant is invalid (e.g. Equivalent Mutant, unintended Syntax Error), construct constructive feedback for the Saboteur.\n"
            "4. Output the feedback text. This will trigger the Saboteur to run again."
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
            "You are the Critic. Ensure the benchmark is unique.\n"
            "Proposed Question Context: {current_target_json}\n"
            "1. Formulate a draft question string based on the target.\n"
            "2. Call `check_uniqueness(question_text=...)`.\n"
            "3. If unique, output 'APPROVED'.\n"
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
            "You are the Assembler.\n"
            "Critic Verdict: {critic_verdict}\n"
            "Target: {current_target_json}\n"
            "Snapshot: {current_snapshot}\n"
            "Mutants: {saboteur_output}\n"
            "1. If Critic Verdict is 'REJECTED', do nothing and output 'SKIPPED'.\n"
            "2. Otherwise, formulate the final Multiple Choice Question.\n"
            "3. CRITICAL: Do not output the JSON as text. You MUST call `save_benchmark_case` with the JSON string.\n"
            "4. Output 'SAVED'."
        )
    )

class PrismaticCoordinator(Agent):
    """Coordinates the loop logic (checking monitor, etc.)."""
    
    async def _run_async_impl(self, ctx: InvocationContext):
        # Check if we should exit
        benchmarks = ctx.session.state.get("generated_benchmarks", [])
        if len(benchmarks) >= 100: # Target 100 benchmarks
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name="exit_loop", args={}))])
            )
        else:
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                content=types.Content(role="model", parts=[types.Part(text=f"Continuing loop... ({len(benchmarks)}/100 generated)")])
            )

def create_prismatic_agent(model_name: str = "gemini-3-pro-preview", api_key_manager: Optional[ApiKeyManager] = None, repo_path: str = ".", concurrency: int = 1) -> Agent:
    """Creates the full Prismatic Generation Agent."""
    
    if api_key_manager:
        semaphore = asyncio.Semaphore(concurrency)
        model = SemaphoreGemini(model=model_name, api_key_manager=api_key_manager, semaphore=semaphore)
    else:
        model = model_name

    auditor = create_auditor_agent(model, repo_path)
    observer = create_observer_agent(model)
    
    # Adversarial Loop: Saboteur <-> Referee
    saboteur = create_saboteur_agent(model)
    referee = create_referee_agent(model)
    adversarial_loop = LoopAgent(
        name="AdversarialLoop",
        sub_agents=[saboteur, referee],
        max_iterations=3 # Limit retries
    )
    
    critic = create_critic_agent(model)
    assembler = create_assembler_agent(model)
    
    process_target_seq = SequentialAgent(
        name="ProcessTarget",
        sub_agents=[auditor, observer, adversarial_loop, critic, assembler]
    )
    
    coordinator = PrismaticCoordinator(name="Coordinator", tools=[FunctionTool(exit_loop)])
    
    main_loop = LoopAgent(
        name="PrismaticLoop",
        sub_agents=[coordinator, process_target_seq],
        max_iterations=200, 
    )
    
    return main_loop
