import json
import pathlib
import re

run_dir = pathlib.Path("benchmark_runs/2026-01-10_16-19-06")
results_file = run_dir / "results.json"

print(f"Analyzing {results_file}...")

with open(results_file, "r") as f:
    data = json.load(f)

target_case = "01: A minimal LlmAgent."
found_result = None

for result in data:
    if result.get("benchmark_name") == target_case:
        found_result = result
        break

if found_result:
    attempts = found_result.get("generation_attempts", [])
    for i, attempt in enumerate(attempts):
        print(f"\n--- Attempt {i+1} ---")
        attempt_str = json.dumps(attempt, default=str)
        
        matches = re.finditer(r'"tool_name": "([^"]+)", "tool_call_id": "([^"]+)"', attempt_str)
        found_tools = False
        for match in matches:
            found_tools = True
            name = match.group(1)
            call_id = match.group(2)
            print(f"Tool Call: {name} (ID: {call_id})")
            
            # Find input
            input_match = re.search(f'"{call_id}".*?"tool_input": ({{[^{{}}]+}})', attempt_str)
            if input_match:
                print(f"  Input: {input_match.group(1)}")

        if not found_tools:
            print("  (No tool calls found)")

else:
    print(f"Could not find result for {target_case}")
