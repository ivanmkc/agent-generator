import asyncio
import sys
import os
from pathlib import Path
from colorama import init, Fore, Style

# Add root to sys.path
if str(Path.cwd()) not in sys.path:
    sys.path.append(str(Path.cwd()))

from benchmarks.answer_generators.gemini_cli_docker import (
    GeminiCliPodmanAnswerGenerator,
)
from benchmarks.tests.integration.test_config import GENERATOR_METADATA

# Initialize colorama
init()

# Ensure dummy key for verification
if "CONTEXT7_API_KEY" not in os.environ:
    os.environ["CONTEXT7_API_KEY"] = "dummy-verification-key"


async def verify_context7():
    config = GENERATOR_METADATA["podman_context7_test_case"]

    # Mock image definitions if needed, or rely on actual
    # We construct a partial one or import standard
    # from benchmarks.answer_generators.gemini_cli_docker.image_definitions import IMAGE_DEFINITIONS
    # But for now let's manually construct to match config

    # We need to supply IMAGE_DEFINITIONS to the generator constructor
    # Let's inspect what IMAGE_DEFINITIONS is
    from benchmarks.answer_generators.gemini_cli_docker.image_definitions import (
        IMAGE_DEFINITIONS,
    )

    generator = GeminiCliPodmanAnswerGenerator(
        dockerfile_dir=Path(config["dockerfile_dir"]),
        image_name=config["image_name"],
        image_definitions=IMAGE_DEFINITIONS,
        model_name="gemini-2.5-flash",
    )

    print(f"{Fore.CYAN}Setting up generator...{Style.RESET_ALL}")
    try:
        await generator.setup()
        print(f"{Fore.GREEN}Setup successful!{Style.RESET_ALL}")

        # Test 1: Functional Check (should have passed in setup)

        # Test 2: Get MCP Tools
        print(f"{Fore.CYAN}Fetching MCP tools...{Style.RESET_ALL}")
        tools = await generator.get_mcp_tools()
        print(f"Tools found: {tools}")

        if "context7" in tools:
            print(f"{Fore.GREEN}Context7 tool found!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Context7 tool NOT found.{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}Verification failed: {e}{Style.RESET_ALL}")
    finally:
        print(f"{Fore.CYAN}Tearing down...{Style.RESET_ALL}")
        await generator.teardown()


if __name__ == "__main__":
    asyncio.run(verify_context7())
