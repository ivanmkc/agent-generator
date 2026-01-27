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

"""
Functional Entry Point for the Agentic Benchmark Generator.

This script orchestrates the generation process using a functional streaming
architecture instead of a stateful agent loop. It uses:
1. Cartographer (Async Generator) -> Scans code lazily
2. AsyncStream (Functional Pipe) -> Maps, Filters, Batches
3. BenchmarkWorker (Stateless Agent) -> Generates content
"""

import argparse
import asyncio
import logging
import json
from pathlib import Path
from typing import Set, Optional

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from tools.benchmark_generator.stream import AsyncStream
from tools.benchmark_generator.cartographer import Cartographer
from tools.benchmark_generator.agents import create_worker_pipeline
from tools.benchmark_generator.models import TargetEntity
from benchmarks.api_key_manager import API_KEY_MANAGER
from tools.benchmark_generator.irt import IRTManager

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AgenticDriver")

async def load_manifest(log_file: Path) -> Set[str]:
    """Loads the set of processed target IDs from the raw JSONL log."""
    processed = set()
    if log_file.exists():
        async with asyncio.Lock(): # Not strictly needed for read, but good habit
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        # Extract target_id or id depending on schema
                        tid = data.get("target_id") or data.get("target", {}).get("id")
                        if tid:
                            processed.add(tid)
                    except json.JSONDecodeError:
                        pass
    return processed

async def process_target(
    target: TargetEntity, 
    model_name: str, 
    repo_path: str,
    concurrency: int,
    stats_file: Optional[str],
    irt_file: Optional[str],
    coverage_file: Optional[str]
) -> bool:
    """
    Executes the agent pipeline for a single target.
    Returns True if a benchmark was successfully generated and saved.
    """
    logger.info(f"▶ Processing Target: {target.id} ({target.type})")
    
    # 1. Setup Isolated Environment
    agent = create_worker_pipeline(
        model_name=model_name, 
        api_key_manager=API_KEY_MANAGER, 
        concurrency=concurrency
    )
    
    # 2. Inject Context into State
    # We use InMemorySessionService for speed and isolation.
    # No need for SQLite here; the artifact (jsonl) is the persistence.
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent, 
        session_service=session_service, 
        app_name="agentic_worker"
    )
    
    session_id = f"run_{target.id.replace('.', '_')}"
    await session_service.create_session(
        session_id=session_id, 
        user_id="gen_user", 
        app_name="agentic_worker"
    )
    
    # Pre-populate state with the specific target and global config
    initial_state = {
        "current_target_json": target.model_dump_json(),
        "repo_path": repo_path,
        "stats_file_path": stats_file,
        "irt_file": irt_file,
        "coverage_file_path": coverage_file,
        # Initialize output slots
        "current_snapshot": "None",
        "saboteur_output": "None",
        "saboteur_feedback": "None",
        "critic_verdict": "None",
        "generated_benchmarks": [] # Helper for uniqueness check within session (empty)
    }
    
    # 3. Execute Run
    # We send a "Start" message to kick off the SequentialAgent
    try:
        success = False
        captured_events = []
        async for event in runner.run_async(
            user_id="gen_user",
            session_id=session_id,
            new_message=types.Content(parts=[types.Part(text="Generate benchmark.")]),
            state_delta=initial_state
        ):
            captured_events.append(event)
            # Check for success signal from Assembler
            if event.author == "Assembler" and event.content:
                for part in event.content.parts:
                    if part.text and "SAVED" in part.text:
                        success = True
                        logger.info(f"✅ Benchmark Saved: {target.id}")
            
            # Optional: Log errors if any
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_response and "error" in str(part.function_response.response).lower():
                         pass # Log deep errors for debugging

        if not success:
            logger.warning(f"⚠️ Failed to generate benchmark for {target.id}. Last 3 events:")
            for e in captured_events[-3:]:
                content = e.content.parts[0].text if (e.content and e.content.parts and e.content.parts[0].text) else "Tool Call/Response"
                logger.warning(f"  [{e.author}]: {content}")

        return success

    except Exception as e:
        logger.error(f"❌ Error processing {target.id}: {e}")
        return False
    finally:
        await runner.close()

async def main():
    parser = argparse.ArgumentParser(description="Functional Agentic Generator")
    parser.add_argument("--repo-path", type=str, default=".", help="Path to repository.")
    parser.add_argument("--model", type=str, default="gemini-3-pro-preview", help="Model name.")
    parser.add_argument("--concurrency", type=int, default=3, help="Concurrent workers.")
    parser.add_argument("--limit", type=int, default=100, help="Max benchmarks to generate.")
    parser.add_argument("--stats-file", type=str, help="Path to usage stats.")
    parser.add_argument("--irt-file", type=str, help="Path to IRT params.")
    parser.add_argument("--coverage-file", type=str, help="Path to coverage data.")
    args = parser.parse_args()

    # 1. Initialize Components
    log_file = Path("agentic_generated_raw.jsonl")
    manifest = await load_manifest(log_file)
    logger.info(f"Loaded manifest with {len(manifest)} processed targets.")
    
    cartographer = Cartographer(
        repo_path=args.repo_path,
        stats_file=args.stats_file,
        cooccurrence_file=None # Can add cli arg if needed
    )

    # 2. Build the Pipeline
    stream = AsyncStream(cartographer.scan(namespace="google.adk"))
    
    # Filtering & Prioritization
    # Note: Cartographer yields all targets. We filter processed ones.
    # Prioritization happens implicitly if Cartographer yields in order, 
    # OR we can collect a batch, sort, and then stream.
    # For now, let's just filter processed and high-value.
    
    worker_fn = lambda target: process_target(
        target, 
        model_name=args.model,
        repo_path=args.repo_path,
        concurrency=args.concurrency,
        stats_file=args.stats_file,
        irt_file=args.irt_file,
        coverage_file=args.coverage_file
    )

    pipeline = (
        stream
        .filter(lambda t: t.id not in manifest)
        .filter(lambda t: t.usage_score > 0) # Focus on used code first
        # Limit the stream to the requested number of *attempts* or *successes*?
        # Ideally successes. But stream slicing is hard on results.
        # We'll just run until we hit the count.
        .par_map(worker_fn, concurrency=args.concurrency)
    )
    
    # 3. Execute
    logger.info("Starting generation pipeline...")
    success_count = 0
    total_processed = 0
    
    async for result in pipeline:
        total_processed += 1
        if result:
            success_count += 1
            if success_count >= args.limit:
                logger.info(f"Target limit {args.limit} reached. Stopping.")
                break
        
        if total_processed % 10 == 0:
            logger.info(f"Progress: {success_count}/{args.limit} benchmarks generated ({total_processed} scanned).")

    logger.info("Run complete.")

import traceback

# ... (imports)

# ... (process_target and main functions)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        print("CRITICAL FAILURE:")
        traceback.print_exc()

