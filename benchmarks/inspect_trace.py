#!/usr/bin/env python3
"""
Utility script to inspect trace logs from a benchmark run.
"""

import argparse
import json
import glob
import os
from datetime import datetime
from pathlib import Path

def find_latest_trace_file(base_dir="benchmark_runs"):
    """Finds the trace.jsonl file in the most recent run directory."""
    runs = glob.glob(os.path.join(base_dir, "*"))
    runs.sort(key=os.path.getmtime, reverse=True)
    
    for run in runs:
        trace_path = os.path.join(run, "trace.jsonl")
        if os.path.exists(trace_path):
            return trace_path
    return None

def print_trace_event(event):
    """Pretty prints a single trace event."""
    etype = event.get("type", "unknown")
    role = event.get("role", "unknown")
    content = event.get("content")
    
    if etype == "message":
        print(f"\n[{role.upper()}]")
        if isinstance(content, str):
            print(content)
        else:
            print(json.dumps(content, indent=2))
            
    elif etype == "tool_use":
        tool_name = event.get("tool_name")
        tool_input = event.get("tool_input")
        print(f"\n[TOOL CALL] {tool_name}")
        print(json.dumps(tool_input, indent=2))
        
    elif etype == "tool_result":
        tool_output = event.get("tool_output")
        print(f"\n[TOOL RESULT]")
        # Truncate long outputs
        if tool_output and len(tool_output) > 500:
             print(tool_output[:500] + "... (truncated)")
        else:
             print(tool_output)
             
    elif etype == "PODMAN_CLI_STDOUT_RAW":
        pass # Ignore raw stdout unless debugging low level
        
    elif etype == "PODMAN_CLI_STDERR":
        print(f"\n[STDERR] {content}")

def main():
    parser = argparse.ArgumentParser(description="Inspect benchmark traces.")
    parser.add_argument("search_term", nargs="?", help="Benchmark name or part of it to filter by.")
    parser.add_argument("--file", "-f", help="Path to trace.jsonl file. Defaults to latest run.")
    parser.add_argument("--list", "-l", action="store_true", help="List all benchmark names in the trace.")
    
    args = parser.parse_args()
    
    trace_file = args.file
    if not trace_file:
        trace_file = find_latest_trace_file()
        
    if not trace_file:
        print("No trace.jsonl file found.")
        return

    print(f"Reading trace from: {trace_file}")
    
    found_any = False
    
    with open(trace_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
                
            if entry.get("event_type") == "test_result":
                data = entry.get("data", {})
                benchmark_name = data.get("benchmark_name", "Unknown")
                
                if args.list:
                    print(f"- {benchmark_name}")
                    continue

                if args.search_term and args.search_term.lower() in benchmark_name.lower():
                    found_any = True
                    print("="*80)
                    print(f"BENCHMARK: {benchmark_name}")
                    print(f"RESULT: {data.get('result')}")
                    print("="*80)
                    
                    trace_logs = data.get("trace_logs")
                    if trace_logs:
                        for log in trace_logs:
                            print_trace_event(log)
                    else:
                        print("(No trace logs recorded for this case)")
                    print("\n")
    
    if args.search_term and not found_any:
        print(f"No benchmark found matching '{args.search_term}'")

if __name__ == "__main__":
    main()
