import json
import pathlib
import re
import argparse
import sys

def estimate_tokens(text):
    if not text: return 0
    return len(str(text)) // 4

def analyze_run(run_dir_path, filter_pattern=None):
    run_path = pathlib.Path(run_dir_path)
    results_file = run_path / "results.json"

    if not results_file.exists():
        # Try finding it in benchmark_runs if a relative name was given
        potential_path = pathlib.Path("benchmark_runs") / run_dir_path / "results.json"
        if potential_path.exists():
            results_file = potential_path
        else:
            print(f"Error: Could not find results.json in {run_path} or {potential_path}")
            return

    print(f"Analyzing {results_file}...")
    
    with open(results_file, "r") as f:
        data = json.load(f)

    matches = []
    for result in data:
        name = result.get("benchmark_name", "")
        if filter_pattern and filter_pattern not in name:
            continue
        matches.append(result)

    if not matches:
        print(f"No benchmarks found matching filter: '{filter_pattern}'")
        return

    print(f"Found {len(matches)} matching cases.\n")

    for result in matches:
        print(f"{'='*80}")
        print(f"CASE: {result.get('benchmark_name')}")
        print(f"RESULT: {result.get('result')}")
        if result.get('validation_error'):
            print(f"ERROR: {result.get('validation_error')}")
        print(f"{'='*80}")

        trace_logs = result.get("trace_logs", [])
        
        # 1. Router Analysis (Architecture Aware)
        router_events = [t for t in trace_logs if t.get("author") == "router"]
        for evt in router_events:
            print(f"[ROUTER]: {evt.get('content')}")

        # 2. Expert Path Detection
        solver_events = [t for t in trace_logs if t.get("author") in ["single_step_solver", "shared_history_solver"]]
        coding_events = [t for t in trace_logs if t.get("author") in ["implementation_planner", "candidate_creator"]]
        
        if solver_events:
            print("\n[PATH]: KNOWLEDGE EXPERT")
        elif coding_events:
            print("\n[PATH]: CODING EXPERT")

        # 3. Tool Usage (Deep Dive)
        print("\n--- Tool Trace ---")
        for evt in trace_logs:
            if evt.get("type") == "tool_use":
                print(f"  > Call: {evt.get('tool_name')}({str(evt.get('tool_input'))[:100]}...)")
            elif evt.get("type") == "tool_result":
                out = str(evt.get('tool_output'))
                print(f"  < Result: {out[:100]}... ({estimate_tokens(out)} tokens)")

        # 4. Final Output Snippet
        output = result.get("output")
        print(f"\n[FINAL OUTPUT]: {json.dumps(output, indent=2)[:500]}...\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze benchmark results.json")
    parser.add_argument("run_id", help="Path to run directory or run ID string")
    parser.add_argument("--filter", "-f", help="Substring to filter benchmark names", default=None)
    
    args = parser.parse_args()
    analyze_run(args.run_id, args.filter)