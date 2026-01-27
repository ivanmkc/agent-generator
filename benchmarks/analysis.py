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
from typing import List, Dict, Any, Set, Optional

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
                    f"### {status_icon} {row['id']}",
                    f"- **Name:** {row['benchmark_name']}",
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


def get_token_usage_stats(results: List[BenchmarkRunResult]) -> pd.DataFrame:
    """
    Analyzes token usage from trace logs.
    Returns a DataFrame with columns: [Benchmark, Generator, Agent, Action, Prompt Tokens, Completion Tokens, Total Tokens]
    """
    token_entries = []

    for r in results:
        if not r.trace_logs:
            continue

        # Group logs by timestamp + author + total_tokens to handle multi-part events (text + tool) from one API call
        unique_generations = {}

        for event in r.trace_logs:
            # Handle Pydantic model vs dict
            details = (
                event.details if hasattr(event, "details") else event.get("details", {})
            )
            if not details:
                continue

            usage = details.get("usage_metadata")
            if not usage:
                # Fallback: check for "stats" in details (Gemini CLI stream-json format)
                usage = details.get("stats")

            if not usage:
                continue

            # normalize usage to dict
            if not isinstance(usage, dict):
                usage = {
                    "prompt_token_count": getattr(usage, "prompt_token_count", 0),
                    "candidates_token_count": getattr(
                        usage, "candidates_token_count", 0
                    ),
                    "total_token_count": getattr(usage, "total_token_count", 0),
                }

            total = usage.get("total_token_count") or usage.get("total_tokens") or 0
            if total == 0:
                continue

            # Identify the event
            timestamp = (
                event.timestamp
                if hasattr(event, "timestamp")
                else event.get("timestamp")
            )
            author = event.author if hasattr(event, "author") else event.get("author")
            if not author:
                author = (
                    event.source
                    if hasattr(event, "source")
                    else event.get("source", "unknown")
                )

            # Create a unique key for this "generation turn"
            key = (timestamp, author, total)

            if key not in unique_generations:
                unique_generations[key] = {
                    "benchmark": r.id,
                    "generator": r.answer_generator,
                    "author": author,
                    "prompt_tokens": usage.get("prompt_token_count")
                    or usage.get("input_tokens")
                    or 0,
                    "completion_tokens": usage.get("candidates_token_count")
                    or usage.get("output_tokens")
                    or 0,
                    "total_tokens": total,
                    "tool_names": set(),
                    "has_text": False,
                }

            # Update the group info based on this specific log event type
            e_type = event.type if hasattr(event, "type") else event.get("type")
            if hasattr(e_type, "value"):
                e_type = e_type.value

            if e_type == "tool_use":
                t_name = (
                    event.tool_name
                    if hasattr(event, "tool_name")
                    else event.get("tool_name")
                )
                if t_name:
                    unique_generations[key]["tool_names"].add(t_name)
            elif e_type == "message":
                role = event.role if hasattr(event, "role") else event.get("role")
                if role == "model":
                    unique_generations[key]["has_text"] = True

        # Convert unique generations to list
        for gen in unique_generations.values():
            tools = list(gen["tool_names"])
            if tools:
                label = f"Tool: {', '.join(sorted(tools))}"
            elif gen["has_text"]:
                label = "Text Generation"
            else:
                label = "Other"

            token_entries.append(
                {
                    "Benchmark": gen["benchmark"],
                    "Generator": gen["generator"],
                    "Agent": gen["author"],
                    "Action": label,
                    "Prompt Tokens": gen["prompt_tokens"],
                    "Completion Tokens": gen["completion_tokens"],
                    "Total Tokens": gen["total_tokens"],
                }
            )

    if not token_entries:
        return pd.DataFrame()

    return pd.DataFrame(token_entries)


def get_tool_success_stats(results: List[BenchmarkRunResult]) -> pd.DataFrame:
    """
    Calculates Success Rate and Lift for each tool used.
    Returns a DataFrame with columns: [tool, times_used, successes, success_rate, lift]
    """
    tool_stats_data = []

    for r in results:
        # Extract unique tools used in this run from trace_logs
        tools_used = set()
        logs = r.trace_logs or []
        for log in logs:
            # Handle Pydantic model vs dict
            e_type = log.type if hasattr(log, "type") else log.get("type")
            if hasattr(e_type, "value"):
                e_type = e_type.value

            if e_type == "tool_use":
                t_name = (
                    log.tool_name if hasattr(log, "tool_name") else log.get("tool_name")
                )
                if t_name:
                    tools_used.add(t_name)

        is_success = r.result == 1

        for tool in tools_used:
            tool_stats_data.append({"tool": tool, "success": is_success})

    if not tool_stats_data:
        return pd.DataFrame()

    df_tools = pd.DataFrame(tool_stats_data)

    # Aggregate
    tool_agg = (
        df_tools.groupby("tool")
        .agg(times_used=("success", "count"), successes=("success", "sum"))
        .reset_index()
    )

    tool_agg["success_rate"] = tool_agg["successes"] / tool_agg["times_used"]

    # Calculate Lift (Difference from overall pass rate)
    overall_pass_rate = (
        sum(1 for r in results if r.result == 1) / len(results) if results else 0
    )
    tool_agg["lift"] = tool_agg["success_rate"] - overall_pass_rate

    return tool_agg.sort_values("times_used", ascending=False)


def format_as_markdown(df: pd.DataFrame, index: bool = False) -> str:
    """Formats a DataFrame as a Markdown table."""
    if df.empty:
        return ""

    # Prepare data (including index if requested)
    data = df.copy()
    if index:
        data.reset_index(inplace=True)

    headers = [str(c) for c in data.columns]
    rows = [[str(x) for x in row] for row in data.values]

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    # Helper to format a single row
    def _fmt(items):
        return (
            "| " + " | ".join(f"{item:<{w}}" for item, w in zip(items, widths)) + " |"
        )

    lines = []
    lines.append(_fmt(headers))
    # Separator
    lines.append("| " + " | ".join("-" * w for w in widths) + " |")
    # Data
    for row in rows:
        lines.append(_fmt(row))

    return "\n".join(lines)
