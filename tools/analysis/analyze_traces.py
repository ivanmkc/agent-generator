import json
import sys

log_file = "benchmark_runs/2025-12-21_12-01-28/trace.jsonl"

try:
    with open(log_file, "r") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("event_type") == "test_result":
                    benchmark_name = entry["data"].get("benchmark_name")
                    trace_logs = entry["data"].get("trace_logs") or []

                    used_tool = False
                    for log in trace_logs:
                        if (
                            log.get("type") == "tool_use"
                            and log.get("tool_name") == "run_adk_agent"
                        ):
                            used_tool = True
                            break

                    if used_tool:
                        print(f"- {benchmark_name}")
            except json.JSONDecodeError:
                continue
except FileNotFoundError:
    print(f"Error: File {log_file} not found.")
