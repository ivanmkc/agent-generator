
import asyncio
import sys
import os
from pathlib import Path
from colorama import init, Fore, Style

# Add root to sys.path
if str(Path.cwd()) not in sys.path:
    sys.path.append(str(Path.cwd()))

from benchmarks import benchmark_orchestrator
from benchmarks.benchmark_candidates import CANDIDATE_GENERATORS
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.logger import JsonTraceLogger, ConsoleBenchmarkLogger, CompositeLogger

# Initialize colorama
init()

async def verify():
    print(f"{Fore.CYAN}Running Standard ADK Agent (Infrastructure Debug)...{Style.RESET_ALL}")

    # 1. Select the Local ADK Generator
    # We want the "Generalist" (single agent) workflow to compare with the basic CLI agent
    target_generator = next(
        (
            g
            for g in CANDIDATE_GENERATORS
            if isinstance(g, AdkAnswerGenerator)
            and "ADK_Single_Agent_Generalist" in g.name
            and "flash" in g.name.lower()
        ),
        None,
    )

    if not target_generator:
        print(f"{Fore.RED}Could not find the 'ADK_Single_Agent_Generalist' generator.{Style.RESET_ALL}")
        # fallback to printing available
        print("Available generators:")
        for g in CANDIDATE_GENERATORS:
            print(f" - {g.name} ({type(g).__name__})")
        return

    print(f"{Fore.GREEN}Found generator: {target_generator.name}{Style.RESET_ALL}")

    # 2. Setup Logger
    # This ensures we get the exact same log format as the full benchmarks
    output_dir = "tmp/debug_adk_infra_logs"
    json_logger = JsonTraceLogger(
        output_dir=output_dir, filename="debug_trace.jsonl"
    )
    console_logger = ConsoleBenchmarkLogger()
    logger = CompositeLogger([console_logger, json_logger])

    # 3. Define a simple test case
    # We can use the existing debug suite or create a temporary one
    suite_path = "benchmarks/benchmark_definitions/debug_suite/benchmark.yaml"

    try:
        print(f"{Fore.CYAN}Starting Orchestrator...{Style.RESET_ALL}")
        
        results = await benchmark_orchestrator.run_benchmarks(
            benchmark_suites=[suite_path],
            answer_generators=[target_generator],
            max_concurrency=1,
            max_retries=0, 
            logger=logger,
        )

        print(f"{Fore.GREEN}Execution completed.{Style.RESET_ALL}")
        print(f"Logs available at: {output_dir}/debug_trace.jsonl")

    except Exception as e:
        print(f"{Fore.RED}Exception during execution: {e}{Style.RESET_ALL}")
    finally:
        # Finalize logger (closes files)
        logger.finalize_run()

if __name__ == "__main__":
    asyncio.run(verify())
