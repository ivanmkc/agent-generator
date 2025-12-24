# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Analysis and reporting functions for benchmarks."""

import re
import difflib
from pathlib import Path
from typing import List

import pandas as pd

from benchmarks.data_models import (
    BenchmarkRunResult,
    BenchmarkResultType,
    BenchmarkType,
)


# ANSI escape codes for colors
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


def extract_error_type(row) -> str:
    """Extracts error type from the result row."""
    if "error_type" in row and pd.notna(row["error_type"]):
        # If it's an Enum object (from pydantic validation), get its value
        et = row["error_type"]
        if hasattr(et, "value"):
            return et.value
        return str(et)
    return "OtherError"


def process_results(
    benchmark_run_results: List[BenchmarkRunResult],
) -> pd.DataFrame:
    """Converts results to a DataFrame and adds derived columns."""
    # Ensure the list is not empty before creating DataFrame
    if not benchmark_run_results:
        return pd.DataFrame()

    raw_results_df = pd.DataFrame([r.model_dump() for r in benchmark_run_results])

    if not raw_results_df.empty:
        # Use parent directory name as suite identifier (e.g. 'api_understanding' instead of 'benchmark.yaml')
        raw_results_df["suite"] = raw_results_df["suite"].apply(
            lambda x: Path(x).parent.name
        )
        raw_results_df["final_error_type"] = raw_results_df.apply(
            extract_error_type, axis=1
        )
        # Ensure status is a string
        raw_results_df["status_str"] = raw_results_df["status"].apply(
            lambda x: x.value if hasattr(x, "value") else str(x)
        )
    return raw_results_df


def print_summary(raw_results_df: pd.DataFrame):
    """Prints a high-level summary of pass rates."""
    if raw_results_df.empty:
        print("No results to summarize.")
        return

    # Calculate counts
    df = raw_results_df.copy()
    # System failures are setup or generation issues
    system_failure_types = [
        BenchmarkResultType.FAIL_SETUP.value,
        BenchmarkResultType.FAIL_GENERATION.value,
    ]
    df["is_crash"] = df["status_str"].isin(system_failure_types)

    summary_df = df.groupby(["answer_generator", "suite"]).agg(
        passed=("result", "sum"),
        crashes=("is_crash", "sum"),
        total=("result", "count"),
    )

    summary_df["system_pass_rate"] = summary_df["passed"] / summary_df["total"]

    summary_df["valid_attempts"] = summary_df["total"] - summary_df["crashes"]
    summary_df["model_accuracy"] = summary_df.apply(
        lambda row: (
            row["passed"] / row["valid_attempts"] if row["valid_attempts"] > 0 else 0.0
        ),
        axis=1,
    )

    print(f"{Bcolors.HEADER}--- Benchmark Summary ---\n{Bcolors.ENDC}")
    display_df = summary_df.copy()
    display_df["system_pass_rate"] = display_df["system_pass_rate"].map("{:.1%}".format)
    display_df["model_accuracy"] = display_df["model_accuracy"].map("{:.1%}".format)
    print(
        display_df[["passed", "crashes", "total", "system_pass_rate", "model_accuracy"]]
    )
    print("\n")


def print_metrics(raw_results_df: pd.DataFrame):
    """Prints performance and cost metrics."""
    if raw_results_df.empty:
        return

    df = raw_results_df.copy()

    def get_meta(row, key):
        if isinstance(row.get("usage_metadata"), dict):
            return row["usage_metadata"].get(key, 0)
        return 0

    df["tokens"] = df.apply(lambda r: get_meta(r, "total_tokens"), axis=1)
    df["cost"] = df.apply(lambda r: get_meta(r, "cost"), axis=1)

    system_failure_types = [
        BenchmarkResultType.FAIL_SETUP.value,
        BenchmarkResultType.FAIL_GENERATION.value,
    ]
    df["is_crash"] = df["status_str"].isin(system_failure_types)

    def aggregate_metrics(grouped):
        return grouped.agg(
            avg_latency=("latency", "mean"),
            avg_tokens=("tokens", "mean"),
            total_cost=("cost", "sum"),
            passed=("result", "sum"),
            crashes=("is_crash", "sum"),
            count=("result", "count"),
        )

    def calculate_rates(metrics_df):
        metrics_df["system_pass_rate"] = metrics_df["passed"] / metrics_df["count"]

        valid_attempts = metrics_df["count"] - metrics_df["crashes"]
        metrics_df["model_accuracy"] = metrics_df.apply(
            lambda row: (
                row["passed"] / valid_attempts[row.name]
                if valid_attempts[row.name] > 0
                else 0.0
            ),
            axis=1,
        )
        return metrics_df.drop(columns=["passed", "crashes"])

    gen_metrics = aggregate_metrics(df.groupby("answer_generator"))
    gen_metrics = calculate_rates(gen_metrics)
    gen_metrics = gen_metrics.rename(columns={"avg_latency": "avg_latency (s)"})

    print(f"{Bcolors.HEADER}--- Metrics by Answer Generator ---\n{Bcolors.ENDC}")
    print(gen_metrics.round(4))
    print("\n")

    detailed_metrics = aggregate_metrics(df.groupby(["answer_generator", "suite"]))
    detailed_metrics = calculate_rates(detailed_metrics)
    detailed_metrics = detailed_metrics.rename(
        columns={"avg_latency": "avg_latency (s)"}
    )

    print(f"{Bcolors.HEADER}--- Metrics by Generator & Suite ---\n{Bcolors.ENDC}")
    print(detailed_metrics.round(4))
    print("\n")


def print_time_profiling(raw_results_df: pd.DataFrame):
    """Analyzes latency and execution time to identify bottlenecks."""
    if raw_results_df.empty:
        return

    print(f"{Bcolors.HEADER}--- Time Profiling Analysis ---\n{Bcolors.ENDC}")

    latency_stats = raw_results_df.groupby("answer_generator")["latency"].describe(
        percentiles=[0.5, 0.75, 0.90, 0.95]
    )[["mean", "min", "50%", "90%", "95%", "max"]]
    print("Latency Statistics (seconds):")
    print(latency_stats.round(2))
    print("\n")

    print("Top 5 Slowest Benchmarks:")
    slowest = raw_results_df.nlargest(5, "latency")[
        ["answer_generator", "suite", "benchmark_name", "latency", "result"]
    ]
    print(slowest.to_string(index=False))
    print("\n")

    def count_trace_events(logs):
        if not isinstance(logs, list):
            return 0, 0
        model_calls = sum(
            1 for e in logs if e.get("type") in ["model_response", "model_call"]
        )
        tool_calls = sum(
            1 for e in logs if e.get("type") in ["tool_code", "tool_execution"]
        )
        return model_calls, tool_calls

    if "trace_logs" in raw_results_df.columns:
        counts = raw_results_df["trace_logs"].apply(
            lambda x: count_trace_events(x if isinstance(x, list) else [])
        )
        raw_results_df["num_model_calls"] = counts.apply(lambda x: x[0])
        raw_results_df["num_tool_calls"] = counts.apply(lambda x: x[1])

        call_stats = raw_results_df.groupby("answer_generator")[
            ["num_model_calls", "num_tool_calls", "latency"]
        ].mean()
        print("Average Complexity (Calls) vs Latency:")
        print(call_stats.round(2))
        print("\n")


def print_detailed_breakdown(raw_results_df: pd.DataFrame):
    """Prints detailed error breakdown and Gemini CLI failures."""
    if raw_results_df.empty:
        return

    failed_df = raw_results_df[raw_results_df["result"] == 0]

    if not failed_df.empty:
        error_counts = (
            failed_df.groupby(["answer_generator", "suite", "final_error_type"])
            .size()
            .reset_index(name="count")
        )

        total_counts = (
            raw_results_df.groupby(["answer_generator", "suite"])
            .size()
            .reset_index(name="total_runs")
        )

        error_summary = pd.merge(
            error_counts, total_counts, on=["answer_generator", "suite"]
        )

        error_summary["failure_ratio"] = (
            error_summary["count"] / error_summary["total_runs"]
        )

        print(f"{Bcolors.HEADER}--- Detailed Error Breakdown ---\n{Bcolors.ENDC}")
        error_summary = error_summary.sort_values(
            ["answer_generator", "suite", "count"], ascending=[True, True, False]
        )
        print(error_summary.to_string(index=False))

        print(f"\n{Bcolors.FAIL}--- DETAILED GEMINI CLI FAILURES ---\n{Bcolors.ENDC}")
        cli_failures = failed_df[
            failed_df["answer_generator"].str.contains("GeminiCliAnswerGenerator")
        ]
        if not cli_failures.empty:
            for _, failure_row in cli_failures.head(3).iterrows():
                print(
                    f"\nBenchmark: {failure_row['benchmark_name']} (Suite:"
                    f" {failure_row['suite']})"
                )
                print(f"Error Type: {failure_row['final_error_type']}")
                print(f"Full Validation Error:\n{failure_row['validation_error']}")
                print("-" * 60)
        else:
            print("No Gemini CLI failures found in this run.")
    else:
        print(f"{Bcolors.OKGREEN}No failures detected!{Bcolors.ENDC}")


def strip_ansi(text: str) -> str:
    """Strips ANSI escape codes from the text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\-_]|[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def generate_detailed_reports(raw_results_df: pd.DataFrame, output_dir: Path):
    """Generates detailed Markdown reports for each answer generator."""
    if raw_results_df.empty:
        return

    print(f"\n{Bcolors.HEADER}--- Generating Detailed Reports ---{Bcolors.ENDC}")
    print(f"Output Directory: {output_dir.absolute()}")

    for generator, group in raw_results_df.groupby("answer_generator"):
        report_lines = [f"# Benchmark Report: {generator}", ""]

        total = len(group)
        passed = len(group[group["result"] == 1])
        pass_rate = (passed / total) * 100 if total > 0 else 0

        report_lines.extend(
            [
                "## Summary",
                f"- **Total Cases:** {total}",
                f"- **Passed:** {passed}",
                f"- **Pass Rate:** {pass_rate:.2f}%",
                "",
                "## Details",
                "",
            ]
        )

        for _, row in group.iterrows():
            status_icon = "✅" if row["result"] == 1 else "❌"
            report_lines.extend(
                [
                    f"### {status_icon} {row['benchmark_name']}",
                    f"- **Suite:** {row['suite']}",
                    f"- **Status:** {row['status']}",
                    f"- **Error Type:** {row['final_error_type']}",
                    "",
                ]
            )

            if row["validation_error"]:
                cleaned_error = strip_ansi(str(row["validation_error"]))
                report_lines.extend(
                    ["**Validation Error:**", "```", cleaned_error, "```", ""]
                )

            if row["rationale"]:
                cleaned_rationale = strip_ansi(str(row["rationale"]))
                report_lines.extend(["**Rationale:**", cleaned_rationale, ""])

                report_lines.extend(
                    [
                        "**Generated Answer:**",
                        "```python",
                        str(row["answer"]),
                        "```",
                    ]
                )

                if row["benchmark_type"] == BenchmarkType.FIX_ERROR.value:
                    fixed_content = row.get("ground_truth", "") or ""

                    generated_content = str(row["answer"])
                    diff = difflib.unified_diff(
                        [l.rstrip() for l in fixed_content.splitlines(keepends=True)],
                        [
                            l.rstrip()
                            for l in generated_content.splitlines(keepends=True)
                        ],
                        fromfile="expected/fixed.py",
                        tofile="generated/answer.py",
                    )

                    diff_text = "\n".join(diff)

                    if diff_text:
                        report_lines.extend(
                            [
                                "**Diff (Expected vs. Generated):**",
                                "```diff",
                                diff_text,
                                "```",
                            ]
                        )
                    else:
                        report_lines.extend(
                            [
                                "**Diff (Expected vs. Generated):**",
                                "```",
                                "No differences.",
                                "```",
                            ]
                        )

                elif row["benchmark_type"] == BenchmarkType.API_UNDERSTANDING.value:
                    expected_content = row.get("ground_truth", "") or ""
                    report_lines.extend(
                        [
                            "**Expected Answer (Example):**",
                            "```python",
                            expected_content,
                            "```",
                        ]
                    )

                elif row["benchmark_type"] == BenchmarkType.MULTIPLE_CHOICE.value:
                    expected_content = row.get("ground_truth", "") or ""
                    report_lines.extend(
                        [
                            f"**Expected Answer:** {expected_content}",
                            "",
                        ]
                    )

                report_lines.extend(["---", ""])

        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in generator)
        file_path = output_dir / f"{safe_name}_report.md"
        with open(file_path, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(report_lines))
            print(f"  - Report saved: {file_path}")
