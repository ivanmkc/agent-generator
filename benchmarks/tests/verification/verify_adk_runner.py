"""Verify Adk Runner module."""

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
from benchmarks.answer_generators.gemini_cli_docker import (
    GeminiCliPodmanAnswerGenerator,
)
from benchmarks.logger import YamlTraceLogger, ConsoleBenchmarkLogger, CompositeLogger
from core.config import PODMAN_CONFIG

# Initialize colorama
init()


async def verify():
    print(f"{Fore.CYAN}Verifying ADK MCP Server fix...{Style.RESET_ALL}")

    # Filter for the relevant generator (mcp-adk-agent-runner)
    target_generator = next(
        (
            g
            for g in CANDIDATE_GENERATORS
            if isinstance(g, GeminiCliPodmanAnswerGenerator)
            and "mcp-adk-agent-runner" in g.image_name
        ),
        None,
    )

    if not target_generator:
        print(
            f"{Fore.RED}Could not find the 'mcp-adk-agent-runner' generator in candidates.{Style.RESET_ALL}"
        )
        return

    print(f"{Fore.GREEN}Found generator: {target_generator.name}{Style.RESET_ALL}")

    # Setup logger
    json_logger = YamlTraceLogger(
        output_dir="tmp/verify_logs", filename="verify_trace.yaml"
    )
    console_logger = ConsoleBenchmarkLogger()
    logger = CompositeLogger([console_logger, json_logger])

    # Define the suite
    suite_path = "benchmarks/benchmark_definitions/debug_suite/benchmark.yaml"

    try:
        # We don't need manual print calls here anymore if we use the logger effectively,
        # but the original script had them. We can keep them or replace them.
        # Let's keep the script structure but rely on the logger for the heavy lifting.

        # logger.log_message(f"Setting up generator...") # The orchestrator does this now inside a section
        # await target_generator.setup() # The orchestrator does this too!

        # Wait, the orchestrator calls generator.setup()!
        # But this script calls it manually *before* creating a proxy?
        # Ah, the script logic is:
        # 1. Setup target_generator (which might be a base image)
        # 2. Check for _base_url and Create a PROXY generator if needed.
        # 3. Pass the (possibly new) generator to orchestrator.

        # So we MUST keep the manual setup here if we want to do the proxy trick.
        # However, calling setup() twice (once here, once in orchestrator) might be bad?
        # AnswerGenerator.setup() is usually idempotent or checks state, but let's be careful.
        # If orchestrator calls setup(), we should probably let it.
        # BUT, the proxy creation depends on `_base_url` which might only be available after setup?
        # Let's assume the existing logic was correct about needing setup first.

        print(f"{Fore.CYAN}Setting up generator...{Style.RESET_ALL}")
        await target_generator.setup()

        # Create proxy if needed (standard pattern)
        if hasattr(target_generator, "_base_url") and target_generator._base_url:
            print(
                f"{Fore.CYAN}Creating proxy for execution at {target_generator._base_url}{Style.RESET_ALL}"
            )
            target_generator = GeminiCliPodmanAnswerGenerator(
                dockerfile_dir=target_generator.dockerfile_dir,
                image_name=target_generator.image_name,
                image_definitions=target_generator._image_definitions,
                model_name=target_generator.model_name,
                context_instruction=target_generator.context_instruction,
                service_url=target_generator._base_url,
            )

        # Note: Orchestrator will call setup() again on the passed generator.
        # If it's a proxy, setup() might be a no-op or just readying clients.

        print(f"{Fore.CYAN}Running debug suite...{Style.RESET_ALL}")
        results = await benchmark_orchestrator.run_benchmarks(
            benchmark_suites=[suite_path],
            answer_generators=[target_generator],
            max_concurrency=1,
            max_retries=0,  # Fail fast
            logger=logger,
        )

        print(f"{Fore.GREEN}Benchmark execution completed.{Style.RESET_ALL}")
        print(
            f"Check 'tmp/verify_logs/verify_trace.yaml' for detailed tool usage logs."
        )

    except Exception as e:
        print(f"{Fore.RED}Exception during verification: {e}{Style.RESET_ALL}")
    finally:
        print(f"{Fore.CYAN}Tearing down...{Style.RESET_ALL}")
        await target_generator.teardown()
        logger.finalize_run()


if __name__ == "__main__":
    asyncio.run(verify())
