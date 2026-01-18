import json
import pathlib
import sys
import re
from collections import Counter

def analyze_trace_logs(trace_logs):
    """
    Analyzes trace logs to extract key execution details.
    """
    analysis = {
        "router_decision": "UNKNOWN",
        "sanitizer_output": None,
        "sanitizer_hallucination": False,
        "tools_called": [],
        "retrieval_steps": 0,
        "coding_attempts": 0,
        "final_code_generated": False,
        "errors": []
    }

    for evt in trace_logs:
        author = evt.get("author", "unknown")
        etype = evt.get("type", "message")
        content = str(evt.get("content", ""))
        tool_name = evt.get("tool_name")

        # 1. Check Router
        if author == "router" and tool_name == "route_task":
            tool_input = evt.get("tool_input") or {}
            analysis["router_decision"] = tool_input.get("category", "UNKNOWN")

        # 2. Check Sanitizer
        if author == "prompt_sanitizer_agent":
            analysis["sanitizer_output"] = content
            # Heuristic: If sanitizer outputs JSON with 'code' or 'fully_qualified_class_name', it's hallucinating.
            if "```json" in content and ("fully_qualified_class_name" in content or '"code":' in content):
                analysis["sanitizer_hallucination"] = True

        # 3. Track Tool Usage
        if etype == "tool_use":
            analysis["tools_called"].append(tool_name)
            if tool_name in ["list_ranked_targets", "search_ranked_targets", "inspect_fqn"]:
                analysis["retrieval_steps"] += 1

        # 4. Coding Loop
        if author == "candidate_creator":
            analysis["coding_attempts"] += 1
            if "```python" in content:
                analysis["final_code_generated"] = True

        # 5. Errors (in tool results)
        if etype == "tool_result" and "Error:" in str(evt.get("tool_output", "")):
             analysis["errors"].append(str(evt.get("tool_output", ""))[:200])

    return analysis

def generate_report(run_id):
    run_dir = pathlib.Path("benchmark_runs") / run_id
    results_file = run_dir / "results.json"

    if not results_file.exists():
        print(f"Error: {results_file} not found.")
        return

    with open(results_file, "r") as f:
        data = json.load(f)

    failures = [r for r in data if r.get("result") == 0]
    
    report_lines = []
    report_lines.append(f"# Forensic Analysis Report: {run_id}")
    report_lines.append(f"**Total Failures:** {len(failures)}\n")

    # Group by Error Type
    error_counts = Counter([r.get("validation_error", "Unknown").split("\n")[0] for r in failures])
    report_lines.append("## Top Error Patterns")
    for err, count in error_counts.most_common(5):
        report_lines.append(f"- **{count}x**: {err}")
    
    report_lines.append("\n## Detailed Case Analysis")

    for case in failures:
        name = case.get("benchmark_name")
        error = case.get("validation_error", "None")
        trace = case.get("trace_logs", [])
        
        analysis = analyze_trace_logs(trace)
        
        report_lines.append(f"\n### Case: `{name}`")
        report_lines.append(f"- **Error:** `{error.splitlines()[0] if error else 'None'}`")
        report_lines.append(f"- **Router:** {analysis['router_decision']}")
        
        if analysis['sanitizer_hallucination']:
            report_lines.append("- **CRITICAL: Sanitizer Hallucination Detected.** The sanitizer outputted structured JSON instead of text.")
        
        if analysis['coding_attempts'] > 0:
            report_lines.append(f"- **Coding Attempts:** {analysis['coding_attempts']}")
            report_lines.append(f"- **Code Generated:** {analysis['final_code_generated']}")
        
        if analysis['retrieval_steps'] > 0:
            report_lines.append(f"- **Retrieval Steps:** {analysis['retrieval_steps']}")
            
        if analysis['tools_called']:
            unique_tools = list(set(analysis['tools_called']))
            report_lines.append(f"- **Tools Used:** {', '.join(unique_tools)}")
        else:
            report_lines.append("- **Tools Used:** NONE")

        if analysis['errors']:
            report_lines.append(f"- **Tool Errors:** {len(analysis['errors'])} found.")
            for e in analysis['errors'][:2]:
                report_lines.append(f"  - `{e}`")

    # Output to file
    output_file = run_dir / "forensic_report.md"
    with open(output_file, "w") as f:
        f.write("\n".join(report_lines))
    
    print(f"Report generated: {output_file}")
    print("\n".join(report_lines[:20])) # Preview

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Find latest run
        import os
        runs = sorted(pathlib.Path("benchmark_runs").glob("202*"))
        if runs:
            latest = runs[-1].name
            print(f"No run ID provided. Analyzing latest: {latest}")
            generate_report(latest)
        else:
            print("Usage: python3 generate_forensic_report.py <run_id>")
    else:
        generate_report(sys.argv[1])
