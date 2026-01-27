#!/usr/bin/env python3
"""
Debugging Tool for ADK Benchmark Runs.

This script analyzes benchmark results and trace logs to help diagnose agent failures.
It can inspect specific benchmark cases, list tool calls, and show tool outputs.
Now includes E2E Analysis Reports.

Usage:
    python tools/debugging.py --run-dir benchmark_runs/<timestamp> --case "01: A minimal LlmAgent."
    python tools/debugging.py --run-dir benchmark_runs/<timestamp> --list-cases
    python tools/debugging.py --run-dir benchmark_runs/<timestamp> --case "01" --report
"""

import json
import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import datetime

# --- Colors for Terminal Output ---
class Bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

def load_results(run_dir: Path) -> list:
    results_file = run_dir / "results.json"
    if not results_file.exists():
        print(f"{Bcolors.FAIL}Error: {results_file} not found.{Bcolors.ENDC}")
        sys.exit(1)
    
    try:
        with open(results_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"{Bcolors.FAIL}Error decoding JSON: {e}{Bcolors.ENDC}")
        sys.exit(1)

def list_failed_cases(run_dir: Path):
    data = load_results(run_dir)
    print(f"\n{Bcolors.HEADER}--- Failed Cases in {run_dir.name} ---{Bcolors.ENDC}")
    
    failures = [r for r in data if r.get("status") != "pass"]
    
    if not failures:
        print(f"{Bcolors.OKGREEN}No failures found!{Bcolors.ENDC}")
        return

    for result in failures:
        print(f"- {result.get('benchmark_name')} ({Bcolors.FAIL}Status: {result.get('status')}{Bcolors.ENDC})")

def analyze_case(run_dir: Path, target_case: str, generate_report: bool = False):
    data = load_results(run_dir)
    found_result = None
    
    # Fuzzy match
    for result in data:
        if target_case.lower() in result.get("benchmark_name", "").lower():
            found_result = result
            break

    if not found_result:
        print(f"{Bcolors.FAIL}Error: Case containing '{target_case}' not found.{Bcolors.ENDC}")
        return

    if generate_report:
        _generate_markdown_report(run_dir, found_result)
    else:
        _print_terminal_analysis(found_result)

def _print_terminal_analysis(result: Dict[str, Any]):
    print(f"\n{Bcolors.HEADER}Analyzing Case: {result.get('benchmark_name')}{Bcolors.ENDC}")
    
    status = result.get("status")
    color = Bcolors.OKGREEN if status == "pass" else Bcolors.FAIL
    print(f"Status: {color}{status}{Bcolors.ENDC}")
    
    if result.get('validation_error'):
        print(f"{Bcolors.WARNING}Validation Error:\n{result.get('validation_error')}{Bcolors.ENDC}")

    attempts = result.get("generation_attempts", [])
    print(f"\nFound {len(attempts)} attempts.")

    for i, attempt in enumerate(attempts):
        print(f"\n{Bcolors.BOLD}=== Attempt {i+1} ==={Bcolors.ENDC}")
        
        trace_logs = attempt.get("trace_logs", [])
        if not trace_logs:
            print("(No trace logs found)")
            continue

        for event in trace_logs:
            # Detect event type (compatible with old and new formats)
            e_type = event.get("type", "unknown")
            role = event.get("role")
            author = event.get("author", "unknown")
            
            # --- MESSAGE (User/System or Model thought) ---
            if e_type == "message":
                if role == "user":
                    content = event.get("content", "")
                    preview = content[:200].replace("\n", " ") + "..." if len(content) > 200 else content
                    print(f"{Bcolors.OKBLUE}[USER -> {author}]{Bcolors.ENDC}: {preview}")
                elif role == "model":
                    content = event.get("content", "")
                    if content:
                        print(f"{Bcolors.OKCYAN}[MODEL ({author}) THOUGHT]:{Bcolors.ENDC}\n{content.strip()}")

            # --- TOOL USE ---
            elif e_type == "tool_use":
                tool_name = event.get("tool_name")
                tool_args = event.get("tool_input")
                print(f"{Bcolors.WARNING}[TOOL CALL ({author})]{Bcolors.ENDC} {tool_name}")
                print(f"  Args: {json.dumps(tool_args, indent=2)}")

            # --- TOOL RESULT ---
            elif e_type == "tool_result":
                tool_name = event.get("tool_name")
                tool_output = event.get("tool_output", "")
                preview = tool_output[:500].replace("\n", " ") + "..." if len(tool_output) > 500 else tool_output
                print(f"{Bcolors.OKGREEN}[TOOL RESULT]{Bcolors.ENDC} {tool_name} -> {preview}")

def _generate_markdown_report(run_dir: Path, result: Dict[str, Any]):
    case_name = result.get('benchmark_name', 'unknown_case')
    safe_name = "".join(c if c.isalnum() else "_" for c in case_name)
    report_path = run_dir / f"analysis_{safe_name}.md"
    
    lines = []
    lines.append(f"# Deep Dive Analysis: {case_name}")
    lines.append(f"**Run:** {run_dir.name}")
    lines.append(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Overview
    status = result.get("status")
    icon = "✅" if status == "pass" else "❌"
    lines.append("## 1. Executive Summary")
    lines.append(f"- **Status:** {icon} {status.upper()}")
    lines.append(f"- **Generator:** {result.get('answer_generator', 'Unknown')}")
    lines.append(f"- **Total Attempts:** {len(result.get('generation_attempts', []))}")
    
    if result.get('validation_error'):
        lines.append("### 🚨 Validation Error")
        lines.append("```text")
        lines.append(result.get('validation_error'))
        lines.append("```")
    
    # Attempts Analysis
    for i, attempt in enumerate(result.get("generation_attempts", [])):
        lines.append(f"## 2. Attempt {i+1} Analysis")
        
        trace_logs = attempt.get("trace_logs", [])
        if not trace_logs:
            lines.append("_No trace logs available for this attempt._")
            continue
            
        # --- Heuristics & Insights ---
        lines.append("### 🧠 Key Insights & Heuristics")
        
        # 1. Context Injection Check
        context_events = [e for e in trace_logs if "API TRUTH CONTEXT" in str(e.get("content", "")) or "knowledge_context" in str(e.get("content", ""))]
        if context_events:
            lines.append(f"- **Context Injection:** ✅ Detected ({len(context_events)} occurrences). Agent likely had access to docs.")
        else:
            lines.append(f"- **Context Injection:** ⚠️ NOT DETECTED. Agent might be flying blind.")
            
        # 2. Loop Usage
        loop_iterations = sum(1 for e in trace_logs if e.get("author") == "run_analysis_agent" or "Execution Logs" in str(e.get("content", "")))
        lines.append(f"- **Refletion Loop:** {loop_iterations} iterations detected.")
        
        # 3. Tool Stats
        tools_used = [e.get("tool_name") for e in trace_logs if e.get("type") == "tool_use"]
        lines.append(f"- **Tools Used:** {', '.join(set(tools_used)) if tools_used else 'None'}")
        
        lines.append("")
        
        # --- Trace Table ---
        lines.append("### 📜 Execution Trace")
        lines.append("| Step | Agent | Type | Content/Action |")
        lines.append("| :--- | :--- | :--- | :--- |")
        
        step_count = 1
        for event in trace_logs:
            e_type = event.get("type", "unknown")
            role = event.get("role", "")
            author = event.get("author", "system")
            
            # Format content for markdown table
            content = ""
            
            if e_type == "message":
                text = event.get("content", "") or ""
                # Truncate for table, full view below?
                preview = text.strip().replace("\n", "<br>").replace("|", "\|")
                if len(preview) > 200:
                    preview = preview[:200] + "..."
                
                type_icon = "👤 Input" if role == "user" else "🤖 Thought"
                content = preview
                
            elif e_type == "tool_use":
                t_name = event.get("tool_name", "")
                t_args = json.dumps(event.get("tool_input", {}))
                type_icon = "🛠️ Call"
                content = f"`{t_name}`<br>`{t_args}`"
                
            elif e_type == "tool_result":
                t_name = event.get("tool_name", "")
                t_out = str(event.get("tool_output", ""))
                type_icon = "📬 Result"
                preview = t_out.strip().replace("\n", "<br>").replace("|", "\|")
                if len(preview) > 200:
                    preview = preview[:200] + "..."
                content = f"**{t_name}**: {preview}"
                
            else:
                type_icon = f"❓ {e_type}"
                content = str(event)

            lines.append(f"| {step_count} | **{author}** | {type_icon} | {content} |")
            step_count += 1
            
        lines.append("")
        
        # --- Full Artifacts ---
        lines.append("### 📂 Generated Code Artifacts")
        # Extract code blocks from model thoughts
        code_blocks = []
        for event in trace_logs:
            if event.get("type") == "message" and event.get("role") == "model":
                text = event.get("content", "")
                matches = re.findall(r"```python\n(.*?)""", text, re.DOTALL)
                for match in matches:
                    code_blocks.append(match)
        
        if code_blocks:
            lines.append(f"Found {len(code_blocks)} Python code blocks generated.")
            lines.append("#### Final Code Candidate:")
            lines.append("```python")
            lines.append(code_blocks[-1]) # Assume last one is final
            lines.append("```")
        else:
            lines.append("_No Python code blocks detected in model output._")

    # Save
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    
    print(f"\n{Bcolors.OKGREEN}Report generated successfully: {report_path}{Bcolors.ENDC}")
    print(f"Use `cat {report_path}` or open it in your editor to view.")

def main():
    parser = argparse.ArgumentParser(description="Analyze ADK benchmark results.")
    parser.add_argument("--run-dir", type=str, required=True, help="Path to the benchmark run directory.")
    parser.add_argument("--case", type=str, help="Name (or substring) of the benchmark case to analyze.")
    parser.add_argument("--list-cases", action="store_true", help="List all failed cases in the run.")
    parser.add_argument("--report", action="store_true", help="Generate a detailed Markdown E2E analysis report.")

    args = parser.parse_args()
    run_path = Path(args.run_dir)

    if args.list_cases:
        list_failed_cases(run_path)
    elif args.case:
        analyze_case(run_path, args.case, args.report)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
