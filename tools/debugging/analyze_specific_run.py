import json
from pathlib import Path
import sys

def analyze():
    # TODO: Remove hardcoding
    run_dir = Path("benchmark_runs/2026-01-16_20-43-28")
    results_file = run_dir / "results.json"
    
    if not results_file.exists():
        print(f"Error: {results_file} does not exist.")
        return

    try:
        with open(results_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading json: {e}")
        return

    print(f"Loaded {len(data)} results.")
    
    # Filter for ADK_HYBRID_V47 failures
    # TODO: Remove all hardcoding
    failures = [d for d in data if d.get("result") == 0 and "ADK_HYBRID_V47" in d.get("generator_name", "")]
    
    print(f"Found {len(failures)} failures for ADK_HYBRID_V47.")
    
    for f in failures:
        print(f"\n--- Case: {f.get('benchmark_name')}")
        print(f"Error: {f.get('validation_error')}")
        
        # Analyze Trace Logs to see Routing Decision
        trace_logs = f.get("trace_logs", [])
        
        # Check Router output
        router_events = [l for l in trace_logs if l.get("author") == "router"]
        for evt in router_events:
            print(f"[Trace] Router: {evt.get('content')}")
            # Check for function call
            if "function_call" in str(evt):
                 print(f"[Trace] Router Call: {evt.get('content')}")
                 
        # Check which expert ran
        coding_events = [l for l in trace_logs if l.get("author") == "implementation_planner"]
        knowledge_events = [l for l in trace_logs if l.get("author") == "single_step_solver"]
        
        if coding_events:
            print(f"[Trace] PATH: CODING EXPERT (Planner ran)")
        if knowledge_events:
            print(f"[Trace] PATH: KNOWLEDGE EXPERT (Solver ran)")
            
        # Check retrieval summary if in Coding path
        if coding_events:
            # Look for retrieval_worker output
            retrieval_logs = [l for l in trace_logs if l.get("author") == "retrieval_worker"]
            for l in retrieval_logs[-1:]:
                print(f"[Trace] Last Retrieval Log: {l.get('content')}")
                
if __name__ == "__main__":
    analyze()
