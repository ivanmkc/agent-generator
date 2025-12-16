
import pytest
import asyncio
from pathlib import Path
from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import GeminiCliPodmanAnswerGenerator
from benchmarks.tests.integration.conftest import has_cmd

@pytest.mark.asyncio
async def test_podman_shared_instance_concurrency(model_name):
    """
    Verifies that a single shared GeminiCliPodmanAnswerGenerator instance
    can handle concurrent setup requests without race conditions.
    """
    if not has_cmd("podman"):
        pytest.skip("Podman not installed")

    # 1. Create a SINGLE shared instance (simulating benchmark_candidates.py)
    # We use a dummy image name to ensure we are testing the setup logic
    generator = GeminiCliPodmanAnswerGenerator(
        dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/base"),
        image_name="gemini-cli:base",
        auto_deploy=True,
        model_name=model_name
    )
    # 2. Define a worker that tries to use the generator
    async def worker(worker_id):
        # This will call setup() internally if not ready
        # We use a trivial command to minimize load but trigger the logic
        try:
            # We access private method to bypass strict prompt formatting of generate_answer
            # effectively simulating _run_cli_command usage
            response, logs = await generator._run_cli_command(
                cli_args=["--version"]
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

    assert len(exceptions) == 0, f"Encountered {len(exceptions)} failures during concurrent access"
    assert len(successes) == num_workers

    # Cleanup
    generator._cleanup_server_container()
