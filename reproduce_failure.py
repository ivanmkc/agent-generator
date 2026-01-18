
import asyncio
import yaml
from pathlib import Path
from benchmarks.benchmark_candidates import CANDIDATE_GENERATORS
from benchmarks.benchmark_orchestrator import run_benchmarks
from benchmarks.data_models import BenchmarkFile

async def main():
    # 1. Select the runner
    runner = next(
        (g for g in CANDIDATE_GENERATORS 
         if "ranked_knowledge" in g.name or "ranked_knowledge" in getattr(g, "image_name", "")),
        None
    )
    if not runner:
        print("Runner not found!")
        return

    print(f"Using runner: {runner.name}")

    # 2. Load the specific benchmark case
    suite_path = Path("benchmarks/benchmark_definitions/debug_suite/benchmark.yaml")
    if not suite_path.exists():
        print(f"Suite not found at {suite_path}")
        # Create a dummy one for the specific case if file missing
        return

    # Filter for the failing case
    with open(suite_path, "r") as f:
        data = yaml.safe_load(f)
        # Keep only fix_error_logic_agent
        data["benchmarks"] = [b for b in data["benchmarks"] if "fix_error_logic_agent" in b["id"]]
    
    # Write temp suite
    temp_suite = Path("temp_debug_suite.yaml")
    with open(temp_suite, "w") as f:
        yaml.dump(data, f)

    # 3. Run it
    results = await run_benchmarks(
        benchmark_suites=[str(temp_suite)],
        answer_generators=[runner],
        max_concurrency=1,
        max_retries=0 # Don't retry, just fail fast
    )

    # 4. Print detailed error
    for res in results:
        print(f"\nResult: {res.status}")
        print(f"Validation Error: {res.validation_error}")
        if res.generation_attempts:
            print(f"Last Attempt Error: {res.generation_attempts[-1].error_message}")
            print(f"Trace Logs:\n{res.generation_attempts[-1].trace_logs}")

    # Cleanup
    temp_suite.unlink()

if __name__ == "__main__":
    asyncio.run(main())
