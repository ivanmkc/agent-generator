import json
from pathlib import Path

def inspect_cases():
    run_dir = Path("benchmark_runs/2026-01-16_20-43-28")
    results_file = run_dir / "results.json"
    
    if not results_file.exists():
        print("Results file not found.")
        return

    with open(results_file, "r") as f:
        data = json.load(f)

    target_ids = [
        "api_understanding:which_plugin_callback_method_can_return_a_value_to",
        "api_understanding:where_does_the_adk_define_the_data_model_for_a_ses",
        "api_understanding:what_is_the_foundational_class_for_all_agents_in_t"
    ]

    for entry in data:
        if entry.get("benchmark_name") in target_ids and entry.get("result") == 0:
            print(f"\n=== Case: {entry.get('benchmark_name')}" ===)
            print(f"Validation Error: {entry.get('validation_error')}")
            
            # Print Final Answer
            print(f"Final Output: {json.dumps(entry.get('output'), indent=2)}")
            
            # Trace Analysis
            logs = entry.get("trace_logs", [])
            
            # 1. Routing
            router_logs = [l for l in logs if l.get("author") == "router"]
            for log in router_logs:
                 print(f"[Router]: {log.get('content')}")
            
            # 2. Retrieval Strategy
            retrieval_logs = [l for l in logs if l.get("author") == "retrieval_worker" or l.get("author") == "knowledge_retrieval_agent"]
            print(f"[Retrieval Steps]: {len(retrieval_logs)} steps.")
            for log in retrieval_logs:
                 # Summarize content
                 content = log.get("content", "")
                 if "function_call" in str(log):
                     print(f"  -> Tool Call: {content[:200]}...")
                 else:
                     print(f"  -> Output: {content[:200]}...")

            # 3. Solver/Creator Output
            solver_logs = [l for l in logs if l.get("author") in ["single_step_solver", "candidate_creator", "shared_history_solver"]]
            for log in solver_logs:
                print(f"[Solver]: {log.get('content')[:500]}...")

if __name__ == "__main__":
    inspect_cases()
