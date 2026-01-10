#!/usr/bin/env python3
"""
Debugging Tool for ADK Benchmark Runs.

This script analyzes benchmark results and trace logs to help diagnose agent failures.
It can inspect specific benchmark cases, list tool calls, and show tool outputs.

Usage:
    python tools/debugging.py --run-dir benchmark_runs/<timestamp> --case "01: A minimal LlmAgent."
    python tools/debugging.py --run-dir benchmark_runs/<timestamp> --list-cases
"""

import json
import argparse
import re
from pathlib import Path
from typing import Optional

def list_failed_cases(run_dir: Path):
    results_file = run_dir / "results.json"
    if not results_file.exists():
        print(f"Error: {results_file} not found.")
        return

    with open(results_file, "r") as f:
        data = json.load(f)

    print(f"\n--- Failed Cases in {run_dir.name} ---")
    for result in data:
        if result.get("status") != "pass":
            print(f"- {result.get('benchmark_name')} (Status: {result.get('status')})")

def analyze_case(run_dir: Path, target_case: str):
    results_file = run_dir / "results.json"
    if not results_file.exists():
        print(f"Error: {results_file} not found.")
        return

    with open(results_file, "r") as f:
        data = json.load(f)

    found_result = None
    for result in data:
        if target_case in result.get("benchmark_name", ""):
            found_result = result
            break

    if not found_result:
        print(f"Error: Case containing '{target_case}' not found.")
        return

    print(f"\nAnalyzing Case: {found_result.get('benchmark_name')}")
    print(f"Status: {found_result.get('status')}")
    print(f"Error Type: {found_result.get('error_type')}")
    if found_result.get('validation_error'):
        print(f"Validation Error:\n{found_result.get('validation_error')}")

    attempts = found_result.get("generation_attempts", [])
    print(f"\nFound {len(attempts)} attempts.")

    for i, attempt in enumerate(attempts):
        print(f"\n=== Attempt {i+1} ===")
        
        trace_logs = attempt.get("trace_logs", [])
        if not trace_logs:
            print("(No trace logs found)")
            continue

        for event in trace_logs:
            role = event.get("role")
            
            # 1. Model Input (User/System)
            if role == "user":
                # Check for tool results
                parts = event.get("details", {}).get("content", {}).get("parts", [])
                for part in parts:
                    if part.get("text"):
                        print(f"[USER]: {part.get('text')[:200]}...")
                    if part.get("function_response"):
                        fr = part.get("function_response")
                        print(f"\n[TOOL RESULT] {fr.get('name')} (ID: {fr.get('id')})")
                        # Try to find the result content
                        resp_content = fr.get("response", {}).get("result", "No result")
                        print(f"  -> {str(resp_content)[:500]}...")

            # 2. Model Output (Thought + Tool Call)
            elif role == "model":
                parts = event.get("details", {}).get("content", {}).get("parts", [])
                
                # Check for Thought/Reasoning (text before tools)
                thought_text = ""
                tool_calls = []
                
                for part in parts:
                    if part.get("text"):
                        thought_text += part.get("text")
                    if part.get("function_call"):
                        tool_calls.append(part.get("function_call"))
                
                if thought_text:
                    print(f"[MODEL THOUGHT]:\n{thought_text.strip()}")
                
                for tc in tool_calls:
                    print(f"\n[TOOL CALL] {tc.get('name')} (ID: {tc.get('id')})")
                    print(f"  Args: {tc.get('args')}")

def main():
    parser = argparse.ArgumentParser(description="Analyze ADK benchmark results.")
    parser.add_argument("--run-dir", type=str, required=True, help="Path to the benchmark run directory.")
    parser.add_argument("--case", type=str, help="Name (or substring) of the benchmark case to analyze.")
    parser.add_argument("--list-cases", action="store_true", help="List all failed cases in the run.")

    args = parser.parse_args()
    run_path = Path(args.run_dir)

    if args.list_cases:
        list_failed_cases(run_path)
    elif args.case:
        analyze_case(run_path, args.case)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()