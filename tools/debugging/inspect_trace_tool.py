import json
import sys

def check_inspect_adk_symbol(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Handle list of results
    if isinstance(data, list):
        results = data
    else:
        results = [data]

    for result in results:
        trace_logs = result.get('trace_logs', [])
        if not trace_logs:
            continue
            
        print(f"--- Benchmark: {result.get('benchmark_name')} ---")
        
        for i, event in enumerate(trace_logs):
            if event.get('type') == 'tool_use' and event.get('tool_name') == 'inspect_adk_symbol':
                print(f"Tool Use: {json.dumps(event.get('tool_input'))}")
                
                # Look for corresponding result
                # Usually the next event or matching ID
                tool_id = event.get('tool_call_id')
                
                # Simple lookahead
                found = False
                for j in range(i + 1, len(trace_logs)):
                    next_event = trace_logs[j]
                    if next_event.get('type') == 'tool_result' and next_event.get('tool_call_id') == tool_id:
                        print(f"Tool Result: {next_event.get('tool_output')}")
                        found = True
                        break
                if not found:
                    print("Tool Result: <NOT FOUND>")
                print("-" * 20)

if __name__ == "__main__":
    check_inspect_adk_symbol("benchmark_runs/2026-01-21_00-07-31/results.json")
