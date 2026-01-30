"""
Analysis script to calculate precise generation latency metrics from benchmark run results.

This script parses `results.json` files using the project's Pydantic data models to ensure
data integrity. It calculates:
1. Average Generation Latency (All Successful Attempts): Time taken to generate output, regardless of correctness.
2. Average Generation Latency (Correct Attempts Only): Time taken to generate a passing answer.
3. Average Prompt Tokens: To correlate latency with context size.

Usage:
    python ai/reports/calculate_attempt_latency.py
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, NamedTuple
import numpy as np

# Add project root to sys.path to allow imports from 'benchmarks' and 'core'
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from benchmarks.data_models import BenchmarkRunResult

class GeneratorStats(NamedTuple):
    """Container for aggregated statistics for a single generator."""
    latencies_all: List[float]
    latencies_correct: List[float]
    prompt_tokens: List[int]
    total_cases: int
    passed_cases: int

def calculate_attempt_latency(results_paths: List[str]) -> None:
    """
    Loads benchmark results and prints a detailed latency analysis table.

    Args:
        results_paths: List of file paths to results.json artifacts.
    """
    
    # Storage: generator_name -> GeneratorStats
    stats: Dict[str, GeneratorStats] = defaultdict(
        lambda: GeneratorStats(
            latencies_all=[], 
            latencies_correct=[], 
            prompt_tokens=[],
            total_cases=0,
            passed_cases=0
        )
    )
    
    for path_str in results_paths:
        path = Path(path_str)
        if not path.exists():
            print(f"Warning: {path} not found.")
            continue
            
        print(f"Loading: {path.name}...")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error reading {path}: {e}")
            continue
            
        for item in raw_data:
            # Validate using Pydantic model for type safety
            try:
                result = BenchmarkRunResult.model_validate(item)
            except Exception as e:
                # print(f"Error validating item in {path.name}: {e}")
                continue
            
            gen_name = result.answer_generator
            s = stats[gen_name]
            
            # Update counts (using a mutable approach for the namedtuple fields lists)
            # NamedTuples are immutable, but the lists inside are mutable references.
            # However, total_cases is an int (immutable). 
            # Better to use a class or update the dict entry completely.
            # Let's switch to a simple class or dict for the accumulator to be safe.
            pass 

    # Re-implementing accumulator with a cleaner dict approach
    # generator -> {'latencies_all': [], 'latencies_correct': [], 'prompt_tokens': [], 'total': 0, 'passed': 0}
    aggregator = defaultdict(lambda: {
        'latencies_all': [],
        'latencies_correct': [],
        'prompt_tokens': [],
        'total': 0,
        'passed': 0
    })

    for path_str in results_paths:
        path = Path(path_str)
        if not path.exists():
            continue
        with open(path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        for item in raw_data:
            result = BenchmarkRunResult.model_validate(item)
            name = result.answer_generator
            agg = aggregator[name]
            
            agg['total'] += 1
            if result.result == 1:
                agg['passed'] += 1
            
            # Check usage metadata for tokens
            if result.usage_metadata and result.usage_metadata.prompt_tokens:
                agg['prompt_tokens'].append(result.usage_metadata.prompt_tokens)

            # Analyze Generation Attempts
            if not result.generation_attempts:
                continue
                
            for attempt in result.generation_attempts:
                # We care about attempts that successfully produced an answer
                # (status="success")
                if attempt.status == "success":
                    agg['latencies_all'].append(attempt.duration)
                    
                    # If the benchmark passed, this attempt was the "winning" one
                    # (Usually there's only one successful attempt if it passed, 
                    # as execution stops on success)
                    if result.result == 1:
                        agg['latencies_correct'].append(attempt.duration)

    # Print Table
    print("\n" + "="*120)
    print(f"{ 'Answer Generator':<65} | {'Lat (All)':<10} | {'Lat (Pass)':<10} | {'Tokens':<8} | {'Pass Rate'}")
    print("-" * 120)
    
    for gen in sorted(aggregator.keys()):
        data = aggregator[gen]
        
        # Calculate Metrics
        avg_lat_all = np.mean(data['latencies_all']) if data['latencies_all'] else 0.0
        avg_lat_pass = np.mean(data['latencies_correct']) if data['latencies_correct'] else 0.0
        avg_tokens = np.mean(data['prompt_tokens']) if data['prompt_tokens'] else 0.0
        pass_rate = (data['passed'] / data['total'] * 100) if data['total'] > 0 else 0.0
        
        # Shorten name for display if needed, but keep full for precision
        display_name = gen.replace("GeminiCliPodmanAnswerGenerator(gemini-2.5-flash, image=", "").replace(")", "")
        
        print(f"{display_name:<65} | {avg_lat_all:>7.2f}s | {avg_lat_pass:>7.2f}s | {avg_tokens:>6.0f}k | {pass_rate:>6.1f}%")
    print("="*120 + "\n")

if __name__ == "__main__":
    # Define the results files to analyze
    files = [
        "tmp/outputs/benchmark_runs/2026-01-30_00-04-29/results.json",
        "tmp/outputs/benchmark_runs/2026-01-30_00-37-18/results.json"
    ]
    calculate_attempt_latency(files)
