#!/usr/bin/env python3
"""Generate Report module."""

import yaml
import sys
import glob
import os
import numpy as np
from pathlib import Path
from tabulate import tabulate
from typing import Optional
from colorama import Fore, Style

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tools.retrieval_dataset_generation.retrieval_engine import RetrievalDataset


def get_latest_log():
    log_files = glob.glob("tmp/logs/validation_run_*.yaml")
    if not log_files:
        return None
    return max(log_files, key=os.path.getctime)


def generate_report(input_path: str, output_path: str, log_path: Optional[str] = None):
    print(f"Loading dataset from {input_path}...")
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    with open(input_path, "r") as f:
        dataset = RetrievalDataset.model_validate(yaml.safe_load(f))

    # Load Trial Logs for granular stats
    target_log = log_path or get_latest_log()
    trial_stats = {}
    global_subset_sizes = []

    if target_log and os.path.exists(target_log):
        print(f"Extracting trial stats from {target_log}...")
        with open(target_log, "r") as f:
            events = list(yaml.safe_load_all(f))
            for e in events:
                if not isinstance(e, dict):
                    continue
                if e.get("event") == "trial_complete":
                    cid = e.get("case_id")
                    size = e.get("subset_size", 0)
                    if cid not in trial_stats:
                        trial_stats[cid] = []
                    trial_stats[cid].append(size)
                    global_subset_sizes.append(size)

    report_lines = []
    report_lines.append("# Retrieval Dataset Analysis Report\n")

    # 1. Executive Summary
    total_cases = len(dataset.cases)
    total_candidates = sum(len(c.candidates) for c in dataset.cases)
    avg_zero_shot = (
        sum(c.metadata.get("zero_context_success_rate", 0.0) for c in dataset.cases)
        / total_cases
        if total_cases > 0
        else 0.0
    )

    avg_contexts = np.mean(global_subset_sizes) if global_subset_sizes else 0.0

    report_lines.append("## 1. Executive Summary\n")
    report_lines.append(f"- **Total Cases Verified:** {total_cases}")
    report_lines.append(f"- **Total Candidates Analyzed:** {total_candidates}")
    report_lines.append(f"- **Average Zero-Context Success Rate:** {avg_zero_shot:.2%}")
    report_lines.append(
        f"- **Average Contexts per Trial:** {avg_contexts:.1f} documents"
    )
    report_lines.append(
        "\nThis report details the empirical relevance of documentation for each benchmark query, identifying 'Critical' documents (high Delta P) and 'Toxic' distractors.\n"
    )

    # 2. Case Breakdown
    report_lines.append("## 2. Case Breakdown\n")

    for case in dataset.cases:
        report_lines.append(f"### Case: `{case.id}`")
        report_lines.append(f"**Query:** {case.query}\n")

        is_skipped = case.metadata.get("skipped", False)
        if is_skipped:
            report_lines.append(
                f"{Fore.YELLOW}**[SKIPPED]** Solvable without context.{Style.RESET_ALL}\n"
            )

        zc = case.metadata.get("zero_context_success_rate", "N/A")
        zc_str = f"{zc:.2%}" if isinstance(zc, float) else zc
        report_lines.append(f"- **Zero-Context Success:** {zc_str}")

        # Trial Stats
        case_sizes = trial_stats.get(case.id, [])
        if case_sizes:
            avg_case_size = np.mean(case_sizes)
            min_size = min(case_sizes)
            max_size = max(case_sizes)
            num_trials = len(case_sizes)
            report_lines.append(f"- **Number of Trials:** {num_trials}")
            report_lines.append(
                f"- **Contexts per Trial:** Avg {avg_case_size:.1f} (Min: {min_size}, Max: {max_size})"
            )

        # Convergence
        trace = case.metadata.get("convergence_trace", [])
        final_uncertainty = trace[-1] if trace else "N/A"
        report_lines.append(
            f"- **Final Max Uncertainty (SE):** {final_uncertainty:.4f}\n"
        )

        # Candidates Table
        candidates = case.candidates
        if not candidates:
            report_lines.append("*No candidates evaluated.*\n")
            continue

        # Sort by Delta P
        sorted_candidates = sorted(
            candidates, key=lambda c: c.metadata.delta_p, reverse=True
        )

        table_data = []
        for c in sorted_candidates:
            dp = c.metadata.delta_p

            # Status Icon
            if dp > 0.2:
                status = "✅ Critical"
            elif dp > 0.05:
                status = "yg Helpful"
            elif dp < -0.1:
                status = "❌ Toxic"
            else:
                status = "⚪ Noise"

            table_data.append(
                [status, f"{dp:+.2f}", c.context_type, f"{c.metadata.n_in}", c.fqn]
            )

        headers = ["Status", "Delta P", "Source", "Trials (In)", "Document FQN"]
        report_lines.append(tabulate(table_data, headers=headers, tablefmt="github"))
        report_lines.append("\n---\n")

    # Write to file
    with open(output_path, "w") as f:
        f.write("\n".join(report_lines))
    print(f"Report generated at {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="retrieval_dataset_verified.yaml")
    parser.add_argument("--output", default="retrieval_analysis_report.md")
    parser.add_argument("--log", help="Path to specific log file")
    args = parser.parse_args()

    generate_report(args.input, args.output, args.log)
