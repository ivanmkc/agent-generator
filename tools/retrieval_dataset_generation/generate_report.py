#!/usr/bin/env python3
import yaml
import sys
from pathlib import Path
from tabulate import tabulate

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tools.retrieval_dataset_generation.lib import RetrievalDataset

def generate_report(input_path: str, output_path: str):
    print(f"Loading dataset from {input_path}...")
    with open(input_path, 'r') as f:
        dataset = RetrievalDataset.model_validate(yaml.safe_load(f))
    
    report_lines = []
    report_lines.append("# Retrieval Dataset Analysis Report\n")
    
    # 1. Executive Summary
    total_cases = len(dataset.cases)
    total_candidates = sum(len(c.candidates) for c in dataset.cases)
    avg_zero_shot = sum(c.metadata.get('zero_context_success_rate', 0.0) for c in dataset.cases) / total_cases if total_cases > 0 else 0.0
    
    report_lines.append("## 1. Executive Summary\n")
    report_lines.append(f"- **Total Cases Verified:** {total_cases}")
    report_lines.append(f"- **Total Candidates Analyzed:** {total_candidates}")
    report_lines.append(f"- **Average Zero-Context Success Rate:** {avg_zero_shot:.2%}")
    report_lines.append("\nThis report details the empirical relevance of documentation for each benchmark query, identifying 'Critical' documents (high Delta P) and 'Toxic' distractors.\n")
    
    # 2. Case Breakdown
    report_lines.append("## 2. Case Breakdown\n")
    
    for case in dataset.cases:
        report_lines.append(f"### Case: `{case.id}`")
        report_lines.append(f"**Query:** {case.query}\n")
        
        zc = case.metadata.get('zero_context_success_rate', 'N/A')
        zc_str = f"{zc:.2%}" if isinstance(zc, float) else zc
        report_lines.append(f"- **Zero-Context Success:** {zc_str}")
        
        # Convergence
        trace = case.metadata.get('convergence_trace', [])
        final_uncertainty = trace[-1] if trace else "N/A"
        report_lines.append(f"- **Final Max Uncertainty (SE):** {final_uncertainty:.4f}\n")
        
        # Candidates Table
        candidates = case.candidates
        if not candidates:
            report_lines.append("*No candidates evaluated.*\n")
            continue
            
        # Sort by Delta P
        sorted_candidates = sorted(candidates, key=lambda c: c.metadata.delta_p, reverse=True)
        
        table_data = []
        for c in sorted_candidates:
            dp = c.metadata.delta_p
            
            # Status Icon
            if dp > 0.2: status = "✅ Critical"
            elif dp > 0.05: status = "yg Helpful"
            elif dp < -0.1: status = "❌ Toxic"
            else: status = "⚪ Noise"
            
            table_data.append([
                status,
                f"{dp:+.2f}",
                c.context_type,
                f"{c.metadata.n_in}",
                c.fqn
            ])
            
        headers = ["Status", "Delta P", "Source", "Trials (In)", "Document FQN"]
        report_lines.append(tabulate(table_data, headers=headers, tablefmt="github"))
        report_lines.append("\n---\n")

    # Write to file
    with open(output_path, 'w') as f:
        f.write("\n".join(report_lines))
    print(f"Report generated at {output_path}")

if __name__ == "__main__":
    generate_report("retrieval_dataset_verified.yaml", "retrieval_analysis_report.md")
