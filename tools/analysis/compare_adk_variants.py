
import asyncio
import sys
import os
from pathlib import Path
from colorama import init, Fore, Style
import json

# Add root to sys.path
if str(Path.cwd()) not in sys.path:
    sys.path.append(str(Path.cwd()))

from benchmarks import benchmark_orchestrator
from benchmarks.benchmark_candidates import CANDIDATE_GENERATORS, api_key_manager, ModelName
from benchmarks.answer_generators.adk_agents import create_default_adk_agent
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.answer_generators.gemini_cli_docker import GeminiCliPodmanAnswerGenerator
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import IMAGE_DEFINITIONS
from benchmarks.logger import YamlTraceLogger, ConsoleBenchmarkLogger, CompositeLogger

# Initialize colorama
init()

async def compare():
    print(f"{Fore.CYAN}Starting ADK Agent Comparison...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}1. Default ADK Agent (Pure LLM) vs 2. Gemini CLI + ADK Python (Containerized){Style.RESET_ALL}")

    # --- Candidate 1: Default ADK Agent (Wrapper) ---
    # We need to wrap the simple LlmAgent in an AdkAnswerGenerator for the orchestrator
    default_agent = create_default_adk_agent(model_name=ModelName.GEMINI_2_5_FLASH)
    candidate_1 = AdkAnswerGenerator(
        agent=default_agent,
        name="Default_ADK_Agent(Flash)",
        api_key_manager=api_key_manager
    )

    # --- Candidate 2: Gemini CLI + ADK Python ---
    # We find this in the existing candidates or create a fresh one
    # Note: Using the specific image `gemini-cli:adk-python`
    image_name = "gemini-cli:adk-python"
    candidate_2 = GeminiCliPodmanAnswerGenerator(
        dockerfile_dir=IMAGE_DEFINITIONS[image_name].source_dir,
        image_name=image_name,
        image_definitions=IMAGE_DEFINITIONS,
        model_name=ModelName.GEMINI_2_5_FLASH,
        context_instruction="Use the available tools and ADK library.",
        api_key_manager=api_key_manager
    )

    generators = [candidate_1, candidate_2]
    
    # --- Setup Logging ---
    output_dir = "tmp/compare_logs"
    json_logger = YamlTraceLogger(
        output_dir=output_dir, filename="compare_trace.yaml"
    )
    console_logger = ConsoleBenchmarkLogger()
    logger = CompositeLogger([console_logger, json_logger])

    # --- Benchmark Suite ---
    # Using debug suite for quick turnaround
    suite_path = "benchmarks/benchmark_definitions/debug_suite/benchmark.yaml"

    try:
        # Run benchmarks sequentially to isolate logs cleanly if needed, though orchestrator handles concurrency
        results = await benchmark_orchestrator.run_benchmarks(
            benchmark_suites=[suite_path],
            answer_generators=generators,
            max_concurrency=1, 
            max_retries=0,
            logger=logger,
        )

        # --- Analysis Report ---
        print("\n" + "="*80)
        print(f"{Fore.YELLOW}COMPARISON REPORT{Style.RESET_ALL}")
        print("="*80)
        
        # We can analyze `results` (BenchMarkResult objects)
        # Assuming `run_benchmarks` returns a list of results (it typically writes to log, but let's check return type if possible, 
        # actually orchestrator returns `List[BenchmarkResult]`)
        
        # Let's manually parse the JSON log for precise token details if the result object doesn't have it all
        # But simpler: rely on the ConsoleLogger summary printed above and just add our own summary.
        
        for res in results:
            gen_name = res.generator_name
            status = f"{Fore.GREEN}PASS{Style.RESET_ALL}" if res.passed else f"{Fore.RED}FAIL{Style.RESET_ALL}"
            duration = f"{res.duration_seconds:.2f}s"
            
            # The result object might not have token usage directly attached in the simple version,
            # but let's try to print what we have.
            print(f"Generator: {Fore.CYAN}{gen_name}{Style.RESET_ALL}")
            print(f"  Result: {status}")
            print(f"  Time:   {duration}")
            print(f"  Error:  {res.error_message if res.error_message else 'None'}")
            print("-" * 40)

    except Exception as e:
        print(f"{Fore.RED}Exception during comparison: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
    finally:
        # Teardown
        for g in generators:
             await g.teardown()
        logger.finalize_run()

if __name__ == "__main__":
    asyncio.run(compare())
