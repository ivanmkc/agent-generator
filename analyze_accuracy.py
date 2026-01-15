import json
import os
from pathlib import Path
from collections import defaultdict
import re

SUITE_SHORTHAND = {
    "api_understanding": "API",
    "fix_errors": "FIX",
    "configure_adk_features_mc": "CFG",
    "diagnose_setup_errors_mc": "DIAG",
    "predict_runtime_behavior_mc": "PRED",
    "debug_single": "DBG1",
    "debug_suite": "DBGS"
}

def shorthand_exp(name):
    name = name.replace("ADK_STATISTICAL_", "V")
    name = name.replace("ADK_KNOWLEDGE_", "K")
    name = name.replace("ADK_CODING_", "C")
    name = name.replace("gemini-2.5-flash", "F")
    name = name.replace("gemini-2.5-pro", "P")
    name = name.replace("Mixed", "M")
    name = name.replace("Loop", "L")
    name = name.replace("Decoupled", "D")
    name = name.replace("GeminiCliPodmanAnswerGenerator", "Podman")
    name = name.replace("GroundTruthAnswerGenerator", "GT")
    # Clean up parentheses
    name = name.replace("(F)", " (F)").replace("(M)", " (M)").replace("(P)", " (P)").replace("(L)", " (L)").replace("(D)", " (D)")
    return name.strip()

def analyze_accuracy():
    benchmark_runs_dir = Path("benchmark_runs")
    if not benchmark_runs_dir.exists():
        return

    # Use a dict to keep only the LATEST run per experiment name
    exp_best_runs = {}

    for run_dir in sorted(benchmark_runs_dir.iterdir(), key=lambda x: x.name, reverse=True):
        if not run_dir.is_dir(): continue
        results_file = run_dir / "results.json"
        if not results_file.exists(): continue

        try:
            with open(results_file, "r") as f:
                run_results = json.load(f)
        except: continue

        if not run_results: continue
        
        exp_name = run_results[0].get("answer_generator", "Unknown")
        if exp_name in exp_best_runs: continue

        suite_stats = defaultdict(lambda: {"passed": 0, "total": 0})
        total_passed = 0
        total_count = 0

        for result in run_results:
            suite_path = result.get("suite", "")
            suite_key = "Unknown"
            for k, v in SUITE_SHORTHAND.items():
                if k in suite_path:
                    suite_key = v
                    break
            
            is_pass = result.get("result") == 1
            suite_stats[suite_key]["total"] += 1
            total_count += 1
            if is_pass:
                suite_stats[suite_key]["passed"] += 1
                total_passed += 1

        exp_best_runs[exp_name] = {
            "exp": shorthand_exp(exp_name),
            "total": f"{(total_passed/total_count)*100:.1f}%",
            "counts": f"{total_passed}/{total_count}",
            "suites": {s: f"{(stats['passed']/stats['total'])*100:.0f}%" for s, stats in suite_stats.items()}
        }

    # Print MD Table
    headers = ["Experiment", "Total", "n", "API", "FIX", "CFG", "DIAG", "PRED"]
    print(f"| {' | '.join(headers)} |")
    print(f"| {' | '.join(['---']*len(headers))} |")
    
    for _, run in exp_best_runs.items():
        s = run["suites"]
        row = [
            run["exp"],
            run["total"],
            run["counts"],
            s.get("API", "-"),
            s.get("FIX", "-"),
            s.get("CFG", "-"),
            s.get("DIAG", "-"),
            s.get("PRED", "-"),
        ]
        print(f"| {' | '.join(row)} |")

if __name__ == "__main__":
    analyze_accuracy()