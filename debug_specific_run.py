import json
import pathlib
import re

# Target Run
run_dir = pathlib.Path("benchmark_runs/2026-01-16_23-39-35")
results_file = run_dir / "results.json"

print(f"Analyzing {results_file}...")

if not results_file.exists():
    print(f"Error: {results_file} not found.")
    exit(1)

with open(results_file, "r") as f:
    data = json.load(f)

# Target Cases to Inspect
targets = [
    "fix_errors:25_multi_agent_interaction_error",
    "fix_errors:15_callbacks"
]

for result in data:
    if result.get("benchmark_name") in targets:
        name = result.get("benchmark_name")
        print(f"\n{'='*80}")
        print(f"CASE: {name}")
        print(f"RESULT: {result.get('result')}")
        print(f"ERROR: {result.get('validation_error')}")
        print(f"{ '='*80}")

        # Check Trace Logs
        trace_logs = result.get("trace_logs", [])
        
        print("\n--- FULL TRACE ---")
        for evt in trace_logs:
            author = evt.get("author", "unknown")
            etype = evt.get("type", "message")
            content = str(evt.get("content", ""))
            
            if etype == "tool_use":
                print(f"[{author}] CALL: {evt.get('tool_name')}({evt.get('tool_input')})")
            elif etype == "tool_result":
                print(f"[{author}] RESULT: {str(evt.get('tool_output'))[:200]}...")
            else:
                print(f"[{author}] {etype.upper()}: {content[:500]}...")
