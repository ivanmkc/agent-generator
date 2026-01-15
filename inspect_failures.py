import json
import argparse
from pathlib import Path
from collections import defaultdict

def inspect_failures(run_id_substring=None):
    benchmark_runs_dir = Path("benchmark_runs")
    if not benchmark_runs_dir.exists():
        print("No benchmark_runs directory found.")
        return

    # Find the requested run or the latest one
    target_run = None
    if run_id_substring:
        matches = [d for d in benchmark_runs_dir.iterdir() if d.is_dir() and run_id_substring in d.name]
        if matches:
            target_run = sorted(matches, key=lambda x: x.name, reverse=True)[0]
    else:
        # Default to latest
        runs = sorted([d for d in benchmark_runs_dir.iterdir() if d.is_dir()], key=lambda x: x.name, reverse=True)
        if runs:
            target_run = runs[0]

    if not target_run:
        print("No matching run found.")
        return

    print(f"Inspecting failures for run: {target_run.name}")
    results_file = target_run / "results.json"
    
    if not results_file.exists():
        print("results.json not found.")
        return

    try:
        with open(results_file, "r") as f:
            results = json.load(f)
    except json.JSONDecodeError:
        print("Invalid results.json")
        return

    failures = [r for r in results if r.get("result") == 0]
    
    if not failures:
        print("No failures found! (100% pass rate)")
        return

    print(f"\nFound {len(failures)} failed cases:")
    
    # Group by error type or suite
    for i, fail in enumerate(failures, 1):
        name = fail.get("benchmark_name", "Unknown")
        suite = fail.get("suite", "Unknown")
        status = fail.get("status", "Unknown")
        val_error = fail.get("validation_error")
        attempts = fail.get("generation_attempts", [])
        
        print(f"\n[{i}] {name} ({suite})")
        print(f"    Status: {status}")
        
        if val_error:
            print(f"    Validation Error: {val_error.strip()}")
        
        # Check generation attempts for specific errors
        for att in attempts:
            if att.get("status") != "success":
                print(f"    Attempt {att.get('attempt_number')} Failed: {att.get('error_message')}")
        
        # Check logs for "ADK Run Failed" if generic
        trace_logs = fail.get("trace_logs", [])
        for log in trace_logs:
             if log.get("type") == "GEMINI_CLIENT_ERROR":
                 print(f"    Client Error Log: {log.get('content')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", nargs="?", help="Substring of run ID")
    args = parser.parse_args()
    inspect_failures(args.run_id)
