"""Test Podman Concurrency module."""

import pytest
import asyncio
from pathlib import Path
from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import (
    GeminiCliPodmanAnswerGenerator,
)
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import (
    IMAGE_DEFINITIONS,
)
from benchmarks.tests.integration.conftest import has_cmd
from benchmarks.api_key_manager import ApiKeyManager


@pytest.mark.asyncio
async def test_podman_shared_instance_concurrency():
    """
    Verifies that a single shared GeminiCliPodmanAnswerGenerator instance
    can handle concurrent setup requests without race conditions.
    """
    model_name = "gemini-2.5-flash"
    if not has_cmd("podman"):
        pytest.skip("Podman not installed")

    # 1. Create a SINGLE shared instance (simulating benchmark_candidates.py)
    # We use a dummy image name to ensure we are testing the setup logic
    generator = GeminiCliPodmanAnswerGenerator(
        image_name="gemini-cli:base",
        image_definitions=IMAGE_DEFINITIONS,
        model_name=model_name,
        api_key_manager=ApiKeyManager(),
    )

    # 2. Define a worker that tries to use the generator
    async def worker(worker_id):
        # This will call setup() internally if not ready
        # We use a trivial command to minimize load but trigger the logic
        try:
            # We access private method to bypass strict prompt formatting of generate_answer
            # effectively simulating _run_cli_command usage
            response, logs = await generator.run_cli_command(
                command_parts=[generator.cli_path, "--version"]
            )
            return True
        except Exception as e:
            return e

    # 3. Launch multiple concurrent workers BEFORE setup is complete
    # This forces them to race for the setup lock
    num_workers = 5
    print(f"\n--- Launching {num_workers} concurrent workers on shared instance ---")

    tasks = [worker(i) for i in range(num_workers)]
    results = await asyncio.gather(*tasks)

    # 4. Verify results
    exceptions = [r for r in results if isinstance(r, Exception)]
    successes = [r for r in results if r is True]

    print(f"Successes: {len(successes)}")
    print(f"Failures: {len(exceptions)}")

    if exceptions:
        print(f"First exception: {exceptions[0]}")

    assert len(successes) == num_workers

    # Cleanup
    await generator.teardown()
