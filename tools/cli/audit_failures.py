#!/usr/bin/env python3
import argparse
import sys
import pathlib
from collections import Counter

# Add project root to sys.path
project_root = str(pathlib.Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from tools.analysis.analyze_benchmark_run import analyze_benchmark_run

class Bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def get_latest_run():
    runs_dir = pathlib.Path("benchmark_runs")
    if not runs_dir.exists(): return None
    runs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime)
    return runs[-1].name if runs else None

def print_summary(run):
    print(f"\n{Bcolors.HEADER}=== Forensic Summary: {run.run_id} ==={Bcolors.ENDC}")
    print(f"Total Failures: {run.total_failures}")
    
    for gen_name, gen in run.generators.items():
        print(f"\n{Bcolors.BOLD}Generator: {gen_name}{Bcolors.ENDC}")
        print(f"  Pass Rate: {gen.pass_rate:.1f}% ({gen.passed_cases}/{gen.total_cases})")
        print(f"  Avg Latency: {gen.avg_latency:.2f}s")
        print(f"  Est. Cost: {gen.estimated_cost:.3f}$")
        
        failures = gen.get_failure_distribution()
        if failures:
            print(f"  {Bcolors.UNDERLINE}Failures by Category:{Bcolors.ENDC}")
            for cat, count in failures.items():
                print(f"    {count:<3} {cat}")

    alerts = run.get_critical_alerts()
    if alerts:
        print(f"\n{Bcolors.FAIL}[CRITICAL ALERTS]{Bcolors.ENDC}")
        for a in alerts:
            reasons = ", ".join([r for r in a["reasons"] if r])
            print(f"  ⚠️ {a['case']} ({reasons})")

def get_report_content(run):
    report_lines = [f"# Forensic Analysis: {run.run_id}\n"]
    
    # Group by Generator for report
    for gen_name, gen in run.generators.items():
        report_lines.append(f"## Generator: {gen_name}")
        report_lines.append(f"- **Pass Rate:** {gen.pass_rate:.1f}%")
        report_lines.append("")
        
        # Sort failed cases by name
        failed_cases = sorted([c for c in gen.cases if c.result_score == 0], key=lambda x: x.benchmark_name)
        
        for f in failed_cases:
            report_lines.append(f"### `{f.benchmark_name}`")
            
            # Use the summarized question
            if f.question_summary:
                 report_lines.append(f"> **Question:** {f.question_summary}")
                 report_lines.append("")

            total_attempts = len(f.attempts)
            for i, att in enumerate(f.attempts):
                report_lines.append(f"#### Attempt {i+1} out of {total_attempts}")
                
                report_lines.append(f"- **Error Category:** {f.primary_failure_category}")
                
                # Dynamic Router Visibility
                if att.has_router:
                    decision = att.router_decision or "IMPLICIT/UNKNOWN"
                    report_lines.append(f"- **Router Decision:** {decision}")
                
                if att.ground_truth or att.answer:
                    report_lines.append("- **Expected:**")
                    report_lines.append(f"```\n{att.ground_truth}\n```")
                    report_lines.append("- **Actual:**")
                    report_lines.append(f"```\n{att.answer}\n```")

                if att.has_sanitizer_hallucination:
                    report_lines.append("- ⚠️ SANITIZER HALLUCINATION DETECTED")
                if att.loop_early_exit:
                    report_lines.append("- ⚠️ EARLY LOOP EXIT DETECTED")
                
                # Show chronological tool sequence with params AND output
                if att.tools_used:
                    report_lines.append(f"- **Tool Chain:**")
                    for t in att.tools_used:
                        name = t['name']
                        args = str(t['args'])
                        output = t.get('output')
                        
                        # Truncate args
                        if len(args) > 80: args = args[:77] + "..."
                        
                        report_lines.append(f"  1. `{name}`({args})")
                        if output:
                             # Truncate output
                             out_str = str(output).replace("\n", " ")
                             if len(out_str) > 100: out_str = out_str[:97] + "..."
                             report_lines.append(f"     -> `{out_str}`")
                report_lines.append("") # Spacing between attempts
                
            report_lines.append("---\n") # Spacing between cases
            
    return "\n".join(report_lines)

def generate_report(run):
    content = get_report_content(run)
    output_path = run.run_dir / "forensic_report_v3.md"
    with open(output_path, "w") as f:
        f.write(content)
    print(f"\nReport written to: {Bcolors.OKBLUE}{output_path}{Bcolors.ENDC}")

def inspect_case(run, target):
    matches = [c for c in run.cases if target in c.benchmark_name]
    if not matches:
        print(f"Case '{target}' not found.")
        return

    for case in matches:
        for i, att in enumerate(case.attempts):
            print(f"\n{Bcolors.HEADER}Inspecting: {case.benchmark_name} (Attempt {i+1}){Bcolors.ENDC}")
            print(f"Category: {case.primary_failure_category}")
            print(f"Final Error: {case.final_validation_error}\n")
            
            for evt in att.trace_logs:
                author = evt.get("author", "unknown")
                type_ = evt.get("type")
                content = evt.get("content")
                
                if type_ == 'tool_use':
                    print(f"{Bcolors.WARNING}[{author}] CALL: {evt.get('tool_name')}{Bcolors.ENDC}")
                elif type_ == 'tool_result':
                    print(f"{Bcolors.OKGREEN}[{author}] RESULT: {str(evt.get('tool_output'))[:100]}...{Bcolors.ENDC}")
                else:
                    print(f"[{author}] {str(content)[:200]}...")
            print(f"\n{'-'*40}")

def main():
    parser = argparse.ArgumentParser(description="Unified ADK Forensic Tool (Refactored)")
    parser.add_argument("run_id", nargs="?", help="Run ID (defaults to latest)")
    parser.add_argument("--report", action="store_true", help="Generate Markdown report")
    parser.add_argument("--inspect", type=str, help="Deep dive specific case substring")
    
    args = parser.parse_args()
    
    run_id = args.run_id or get_latest_run()
    if not run_id:
        print("No runs found.")
        return

    run = analyze_benchmark_run(run_id)
    
    if args.inspect:
        inspect_case(run, args.inspect)
    else:
        print_summary(run)
        if args.report:
            generate_report(run)

if __name__ == "__main__":
    main()