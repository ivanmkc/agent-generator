import json
import pandas as pd
from pathlib import Path

# --- Configuration ---
# Paths are absolute or relative to the current working directory (mcp_server)
LOCAL_RUNS = {
    "Run 3 (14:31)": "tmp/outputs/benchmark_runs/2026-02-02_14-31-38",
    "Run 2 (12:09)": "tmp/outputs/benchmark_runs/2026-02-02_12-09-15",
    "Run 1 (01:51)": "tmp/outputs/benchmark_runs/2026-02-02_01-51-17",
}

EXTERNAL_RUNS = {
    "Ext Run (14:12)": "/Users/ivanmkc/Documents/code/agent-generator/tmp/outputs/benchmark_runs/2026-02-02_14-12-44",
    "Ext Run (14:22)": "/Users/ivanmkc/Documents/code/agent-generator/tmp/outputs/benchmark_runs/2026-02-02_14-22-04",
    "Ext Run (14:30)": "/Users/ivanmkc/Documents/code/agent-generator/tmp/outputs/benchmark_runs/2026-02-02_14-30-54",
    "Ref Run (12:50)": "/Users/ivanmkc/Documents/code/agent-generator/tmp/outputs/benchmark_runs/2026-02-02_12-50-41",
    "Baseline (Jan 30)": "/Users/ivanmkc/Documents/code/agent-generator/tmp/outputs/benchmark_runs/2026-01-30_00-04-29",
}

# --- Helpers ---

def load_results(path_str):
    path = Path(path_str) / "results.json"
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        if isinstance(data, dict) and 'results' in data:
            return data['results']
        return data
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return []

def calculate_stats(results, label):
    # Filter for ranked knowledge or mcp generators
    # We broaden the filter to catch "codebase_knowledge" or "ranked" to ensure we capture relevant runs
    filtered_results = [
        r for r in results 
        if "ranked" in r.get('answer_generator', '').lower() 
        or "mcp" in r.get('answer_generator', '').lower()
        or "codebase_knowledge" in r.get('answer_generator', '').lower()
    ]
    
    if not filtered_results:
        # Fallback: if it's a single-generator run, assume it's the target
        generators = set(r.get('answer_generator') for r in results)
        if len(generators) == 1:
             filtered_results = results
        else:
             return {"label": label, "total": 0, "pass": 0, "pass_rate": 0.0, "raw_results": [], "agent_id": "None"}

    total = len(filtered_results)
    passed = sum(1 for r in filtered_results if r.get('status') == 'pass')
    
    # Extract Agent ID (Generator Name)
    # We take the most common one in the filtered results
    agent_ids = [r.get('answer_generator', 'Unknown') for r in filtered_results]
    agent_id = max(set(agent_ids), key=agent_ids.count) if agent_ids else "Unknown"

    return {
        "label": label,
        "total": total,
        "pass": passed,
        "pass_rate": (passed / total) * 100 if total > 0 else 0.0,
        "agent_id": agent_id,
        "raw_results": filtered_results
    }

def get_suite_stats(results):
    suites = {}
    for r in results:
        suite = r.get('benchmark_name', '').split(':')[0]
        if not suite: suite = "unknown"
        if suite not in suites:
            suites[suite] = {'total': 0, 'pass': 0}
        suites[suite]['total'] += 1
        if r.get('status') == 'pass':
            suites[suite]['pass'] += 1
    return suites

# --- Processing ---

all_stats = []

# Process Local Runs
print(f"\nProcessing {len(LOCAL_RUNS)} Local Runs (mcp_server/tmp/)...")
for label, path in LOCAL_RUNS.items():
    s = calculate_stats(load_results(path), label)
    s['group'] = 'Local (mcp_server)'
    all_stats.append(s)

# Process External Runs
print(f"Processing {len(EXTERNAL_RUNS)} External Runs (agent_generator/tmp/)...")
for label, path in EXTERNAL_RUNS.items():
    s = calculate_stats(load_results(path), label)
    s['group'] = 'External (agent_generator)'
    all_stats.append(s)

# --- Summary Table ---
print("\n--- Benchmark Summary by Location ---")
df_summary = pd.DataFrame([{k: v for k, v in s.items() if k != 'raw_results'} for s in all_stats])
# Reorder columns
cols = ['group', 'label', 'pass_rate', 'pass', 'total', 'agent_id']
print(df_summary[cols].sort_values(['group', 'label'], ascending=[False, False]).to_markdown(index=False))

# --- Breakdown Table ---
print("\n--- Suite Breakdown ---")
all_suite_data = [get_suite_stats(s['raw_results']) for s in all_stats]
all_suite_names = sorted(set().union(*[d.keys() for d in all_suite_data]))

breakdown_rows = []
for suite in all_suite_names:
    row = {"Suite": suite}
    for i, stats_obj in enumerate(all_stats):
        col_name = f"{stats_obj['group']} - {stats_obj['label']}"
        # Shorten for display
        col_name = col_name.replace("Local (mcp_server) - ", "L:").replace("External (agent_generator) - ", "E:")
        
        suite_stats = all_suite_data[i].get(suite, {'total': 0, 'pass': 0})
        rate = (suite_stats['pass'] / suite_stats['total'] * 100) if suite_stats['total'] else 0
        row[col_name] = f"{rate:.1f}%"
    breakdown_rows.append(row)

df_breakdown = pd.DataFrame(breakdown_rows)
print(df_breakdown.to_markdown(index=False))