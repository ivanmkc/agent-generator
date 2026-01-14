
import asyncio
import sys
from benchmarks.benchmark_orchestrator import BenchmarkOrchestrator
from benchmarks.benchmark_candidates import CANDIDATE_GENERATORS

async def main():
    orchestrator = BenchmarkOrchestrator(
        generators=CANDIDATE_GENERATORS,
        parallel_limit=5
    )
    
    # Filter for V45
    target_generators = [
        g for g in CANDIDATE_GENERATORS 
        if "V45" in g.name
    ]
    
    if not target_generators:
        print("Error: V45 generator not found in candidates.")
        return

    print(f"Running V45 with {len(target_generators)} generators...")
    await orchestrator.run_benchmarks(target_generators=target_generators)

if __name__ == "__main__":
    asyncio.run(main())
