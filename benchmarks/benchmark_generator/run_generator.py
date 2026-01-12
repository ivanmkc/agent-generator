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

"""CLI tool for generating benchmarks."""

import argparse
import asyncio
import logging
from pathlib import Path
import yaml
import json

from benchmarks.data_models import BenchmarkFile
from benchmarks.benchmark_generator.agents import create_prismatic_agent
from google.adk.runners import Runner
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai import types
from benchmarks.api_key_manager import API_KEY_MANAGER
from benchmarks.benchmark_generator.logger import PrismaticLogger


async def main():
    parser = argparse.ArgumentParser(description="Generate benchmarks for ADK.")
    parser.add_argument(
        "--type",
        choices=["prismatic_adk"],
        default="prismatic_adk",
        help="Type of benchmark to generate (default: prismatic_adk).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to save generated benchmark cases.",
    )
    parser.add_argument(
        "--suite-name",
        type=str,
        default="generated_suite",
        help="Name of the benchmark suite.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3-pro-preview",
        help="Model to use for generation.",
    )
    parser.add_argument("--repo-path", type=str, default=".", help="Path to the repository to scan.")
    parser.add_argument("--coverage-file", type=str, help="Path to coverage data.")
    parser.add_argument("--irt-file", type=str, help="Path to IRT data.")
    parser.add_argument(
        "--namespace",
        type=str,
        required=True,
        help="Namespace to restrict the scan to (e.g., 'google.adk'). Only entities within this namespace will be targeted.",
    )
    parser.add_argument(
        "--cooccurrence-file",
        type=str,
        required=True,
        help="Path to the JSON file containing co-occurrence data for context calculation.",
    )
    parser.add_argument("--concurrency", type=int, default=1, help="Max concurrent LLM requests.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of benchmarks to generate (default: 100).")
    parser.add_argument("--session-db", type=str, default="prismatic_sessions.db", help="Path to SQLite session database.")

    args = parser.parse_args()

    benchmarks = []

    if args.type == "prismatic_adk":
        print(f"Starting Prismatic ADK Generator (Model: {args.model})...")
        print(f"  Repo Path: {args.repo_path}")
        print(f"  Namespace: {args.namespace or 'All'}")
        print(f"  Co-occurrence: {args.cooccurrence_file}")
        print(f"  Limit: {args.limit}")
        
        agent = create_prismatic_agent(
            model_name=args.model, 
            api_key_manager=API_KEY_MANAGER, 
            repo_path=args.repo_path, 
            concurrency=args.concurrency
        )
        logger = PrismaticLogger()
        
        # Setup Runner with Persistence
        session_service = SqliteSessionService(db_path=args.session_db)
        runner = Runner(agent=agent, session_service=session_service, app_name="benchmark_generator")
        
        session_id = "prismatic_run_0"
        
        # Check for existing session
        existing_session = await session_service.get_session(session_id=session_id, user_id="user", app_name="benchmark_generator")
        
        state_delta = {}
        
        if existing_session:
            print(f"Resuming existing session: {session_id}")
            # Ensure required keys exist (if schema changed or new keys added)
            if "generated_benchmarks" not in existing_session.state:
                state_delta["generated_benchmarks"] = []
            # Do NOT overwrite scanned_targets or processed_targets_list if they exist
        else:
            print(f"Creating new session: {session_id}")
            await session_service.create_session(session_id=session_id, user_id="user", app_name="benchmark_generator")
            # Initialize full state
            state_delta = {
                "generated_benchmarks": [],
                "scanned_targets": [],
                "processed_targets_list": [],
                "current_target_json": "None",
                "current_snapshot": "None",
                "saboteur_output": "None",
                "observer_status": "None",
                "assembler_status": "None",
                "saboteur_feedback": "None",
                "critic_verdict": "None",
            }
        
        # Always update configuration from CLI args (overrides session state)
        state_delta["repo_path"] = str(args.repo_path)
        state_delta["output_dir"] = str(args.output_dir)
        if args.namespace:
            state_delta["target_namespace"] = args.namespace
        state_delta["cooccurrence_file"] = args.cooccurrence_file
        
        if args.coverage_file:
            state_delta["coverage_file_path"] = args.coverage_file
        if args.irt_file:
            state_delta["irt_file"] = args.irt_file
        
        # Get session object for current state
        session = await session_service.get_session(session_id=session_id, user_id="user", app_name="benchmark_generator")
        
        # Run the agent in a loop until target is reached
        target_count = args.limit
        current_count = len(session.state.get("generated_benchmarks", []))
        
        while current_count < target_count:
            print(f"[Coordinator]: Continuing loop... ({current_count}/{target_count} generated)")
            
            # Send the message to trigger next cycle
            # Use 'Start' if current_count is 0, else 'Continue'
            trigger_msg = "Start generation" if current_count == 0 else "Continue generation"
            
            async for event in runner.run_async(
                user_id="user",
                session_id=session_id,
                new_message=types.Content(parts=[types.Part(text=trigger_msg)]),
                state_delta=state_delta if current_count == 0 else None
            ):
                logger.log_event(event)
            
            # Refresh session to get latest state from DB
            session = await session_service.get_session(session_id=session_id, user_id="user", app_name="benchmark_generator")
            new_count = len(session.state.get("generated_benchmarks", []))
            
            # Use raw file as fallback for count if state persistence is buggy
            if Path("prismatic_generated_raw.jsonl").exists():
                with open("prismatic_generated_raw.jsonl", "r") as f:
                    raw_count = sum(1 for _ in f)
                new_count = max(new_count, raw_count)

            if new_count == current_count:
                 # It might have failed one turn, let's not give up immediately
                 # But for now, we'll use a small limit to avoid infinite loops in failure
                 pass

            current_count = new_count
            if current_count >= target_count: break
        
        # Extract results
        generated_data = session.state.get("generated_benchmarks", [])
        print(f"Generation complete. Found {len(generated_data)} benchmarks in session state.")
        
        # Convert JSON dicts to Pydantic models (MultipleChoiceBenchmarkCase)
        from benchmarks.data_models import MultipleChoiceBenchmarkCase
        
        for data in generated_data:
            try:
                # Ensure it matches the schema expected by BenchmarkFile
                if isinstance(data, str):
                    data = json.loads(data)
                
                # Check/Fix missing fields if necessary
                if "benchmark_type" not in data:
                    data["benchmark_type"] = "multiple_choice"

                case = MultipleChoiceBenchmarkCase.model_validate(data)
                benchmarks.append(case)
            except Exception as e:
                print(f"Failed to parse benchmark case: {e}")
                # print(f"Data: {data}")

    if benchmarks:
        benchmark_file = BenchmarkFile(benchmarks=benchmarks)
        
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output_yaml = args.output_dir / "benchmark.yaml"
        with open(output_yaml, "w", encoding="utf-8") as f:
            yaml.dump(benchmark_file.model_dump(mode="json"), f, sort_keys=False)

        print(f"Generated {len(benchmarks)} benchmarks in {args.output_dir}")
        print(f"Suite YAML saved to {output_yaml}")
    else:
        print("No benchmarks were generated.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
