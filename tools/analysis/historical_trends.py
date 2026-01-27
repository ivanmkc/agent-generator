"""
Analysis of pass rates over time across multiple runs.

This script scans the `benchmark_runs/` directory to calculate weighted pass rates
for benchmark cases. It applies a recency decay factor to prioritize recent results,
helping identify "flaky" tests versus consistently broken features.

Usage:
    python tools/analysis/historical_trends.py
"""

import json
import yaml
import pathlib
import sys
from collections import defaultdict
from typing import Dict, List, Tuple
import math

# Configuration
RUNS_DIR = pathlib.Path("benchmark_runs")
MIN_RUNS = 2  # Minimum number of runs a case must appear in to be reported
DECAY_FACTOR = 0.8  # Weight multiplier for older runs (1.0 = equal weight, 0.5 = heavy bias to recent)


def analyze_historical_pass_rates():
    """
    Analyzes historical benchmark runs to identify persistent failure cases.
    Weights more recent runs higher.
    """
    if not RUNS_DIR.exists():
        print(f"Error: {RUNS_DIR} does not exist.")
        return

    # Data structure: benchmark_name -> list of results (1 for pass, 0 for fail) in reverse chronological order
    case_results: Dict[str, List[int]] = defaultdict(list)

    run_count = 0
    print(f"Scanning {RUNS_DIR} for trace.yaml files (Weighted by Recency)...")

    # Sort by date desc (Most recent first)
    run_dirs = sorted([d for d in RUNS_DIR.iterdir() if d.is_dir()], reverse=True)

    for run_dir in run_dirs:
        log_file = run_dir / "trace.yaml"
        if not log_file.exists():
            continue

        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                run_processed = False
                for event in yaml.safe_load_all(f):
                    if event is None:
                        continue
                    if event.get("event_type") == "test_result":
                        data = event.get("data", {})
                        # Prioritize 'id' (unambiguous) over 'benchmark_name' (historical)
                        name = data.get("id") or data.get("benchmark_name")
                        result = data.get("result")

                        if name and result:
                            case_results[name].append(1 if result == "pass" else 0)
                            run_processed = True

                if run_processed:
                    run_count += 1

        except Exception as e:
            print(f"Error processing {log_file}: {e}")

    print(f"\nAnalyzed {run_count} runs.")
    print("-" * 85)
    print(f"{ 'Benchmark Case':<60} | {'Weighted Pass':<13} | {'Total Runs':<10}")
    print("-" * 85)

    # Calculate weighted pass rates
    results = []
    for name, results_list in case_results.items():
        if len(results_list) < MIN_RUNS:
            continue

        # results_list is [most_recent, ..., oldest]
        weighted_sum = 0.0
        total_weight = 0.0

        for i, res in enumerate(results_list):
            weight = math.pow(DECAY_FACTOR, i)
            weighted_sum += res * weight
            total_weight += weight

        weighted_pass_rate = (weighted_sum / total_weight) * 100

        results.append(
            {
                "name": name,
                "weighted_pass_rate": weighted_pass_rate,
                "total": len(results_list),
            }
        )

    # Sort: Weighted Pass Rate (asc), then Total Runs (desc)
    results.sort(key=lambda x: (x["weighted_pass_rate"], -x["total"]))

    for res in results:
        name_display = (
            (res["name"][:57] + "...") if len(res["name"]) > 57 else res["name"]
        )
        print(
            f"{name_display:<60} | {res['weighted_pass_rate']:11.1f}% | {res['total']:<10}"
        )

    print("-" * 85)
    print(
        f"\nNote: Weighted Pass Rate uses a decay factor of {DECAY_FACTOR} per previous run."
    )


if __name__ == "__main__":
    analyze_historical_pass_rates()
