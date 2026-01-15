import sqlite3
import json
import os
from pathlib import Path

# DB Config
DB_PATH = "benchmarks/analysis_cache.db"
RUNS_DIR = Path("benchmark_runs")

def get_target_failures():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        # Target specific failure modes in API Understanding
        return conn.execute("""
            SELECT run_id, benchmark_name, attempt_number, llm_root_cause, generator
            FROM failures 
            WHERE suite='api_understanding' 
              AND (llm_root_cause LIKE '%Hallucination%' OR llm_root_cause LIKE '%Context Starvation%')
            ORDER BY run_id DESC
            LIMIT 20
        """).fetchall()

def extract_tool_chain(run_id, benchmark_name, attempt_number):
    log_file = RUNS_DIR / run_id / "trace.jsonl"
    if not log_file.exists():
        return None

    tool_chain = []
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            try:
                event = json.loads(line)
                # Find the test result to match benchmark/attempt
                if event.get("event_type") == "test_result":
                    data = event.get("data", {})
                    if data.get("benchmark_name") == benchmark_name:
                        # Extract the trace logs for the specific attempt
                        attempts = data.get("generation_attempts", [])
                        trace_logs = []
                        for att in attempts:
                            if att.get("attempt_number") == attempt_number:
                                trace_logs = att.get("trace_logs", [])
                                break
                        if not trace_logs:
                             trace_logs = data.get("trace_logs", [])

                        # Now parse the trace logs for tool usage
                        for item in trace_logs:
                            if item.get("type") == "tool_use":
                                name = item.get("tool_name")
                                args = item.get("tool_input")
                                call_id = item.get("tool_call_id")
                                tool_chain.append({
                                    "type": "call",
                                    "name": name,
                                    "args": args,
                                    "id": call_id
                                })
                            elif item.get("type") == "tool_result":
                                name = item.get("tool_name")
                                output = item.get("tool_output")
                                call_id = item.get("tool_call_id")
                                # Find corresponding call
                                for call in reversed(tool_chain):
                                    if call["id"] == call_id and call["type"] == "call":
                                        call["output"] = output
                                        break
                        return tool_chain
            except:
                continue
    return None

def main():
    failures = get_target_failures()
    print(f"Found {len(failures)} failures for Deep Dive.\n")

    for fail in failures:
        print(f"=== [{fail['llm_root_cause']}] {fail['benchmark_name']} ===")
        print(f"Agent: {fail['generator']}")
        
        chain = extract_tool_chain(fail['run_id'], fail['benchmark_name'], fail['attempt_number'])
        
        if not chain:
            print("  (No trace found)")
            continue

        # Filter for relevant tools
        relevant_chain = [t for t in chain if t['name'] in ('save_relevant_modules', 'get_module_help', 'search_files')]
        
        if not relevant_chain:
            print("  (No retrieval tools called)")
        
        for tool in relevant_chain:
            name = tool['name']
            args = tool.get('args')
            output = tool.get('output', 'N/A')
            
            # Formatting
            if name == 'save_relevant_modules':
                modules = args.get('modules', []) if args else []
                print(f"  -> SEED SELECTION: {modules}")
            
            elif name == 'get_module_help':
                mod_target = args.get('module_name') if args else '?'
                status = "OK"
                if "No module named" in str(output) or "not found" in str(output) or output == "":
                    status = "MISSING"
                elif "Empty" in str(output): # Some tools return "Empty docstring"
                    status = "EMPTY"
                
                print(f"     -> FETCH '{mod_target}': {status}")
                if status != "OK":
                    print(f"        Raw Output: {str(output)[:100]}...")

            elif name == 'search_files':
                query = args.get('query') if args else '?'
                print(f"     -> SEARCH '{query}'")
                print(f"        Result: {str(output)[:100]}...")

        print("\n")

if __name__ == "__main__":
    main()
