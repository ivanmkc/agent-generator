import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
import difflib
import re
from typing import List
from pydantic import TypeAdapter
from benchmarks.data_models import BenchmarkRunResult, BenchmarkResultType
from benchmarks.benchmark_candidates import CANDIDATE_GENERATORS
from tools.analysis.analyze_benchmark_run import analyze_benchmark_run

# --- Constants ---
BENCHMARK_RUNS_DIR = Path("benchmark_runs")


# --- Helper Functions ---


def load_run_options():
    """Returns a list of available benchmark run directories, sorted by modification time (newest first)."""
    if not BENCHMARK_RUNS_DIR.exists():
        return []
    
    # Sort by modification time to ensure latest runs appear first regardless of naming
    runs = sorted(
        [d for d in BENCHMARK_RUNS_DIR.iterdir() if d.is_dir()],
        key=os.path.getmtime,
        reverse=True
    )
    
    return [d.name for d in runs]


@st.cache_data
def load_results(run_id) -> List[BenchmarkRunResult]:
    """Loads results.json for a given run ID into a list of BenchmarkRunResult objects."""
    # Ensure fresh load
    path = BENCHMARK_RUNS_DIR / run_id / "results.json"
    if not path.exists():
        return []

    with open(path, "r") as f:
        data = json.load(f)

    # Validate and parse into objects
    results = TypeAdapter(List[BenchmarkRunResult]).validate_python(data)
    
    return results


@st.cache_data
def load_traces(run_id):
    """Loads trace.jsonl and indexes it by benchmark_name.

    Returns: Dict[benchmark_name, List[trace_event]]
    """
    path = BENCHMARK_RUNS_DIR / run_id / "trace.jsonl"
    if not path.exists():
        return {}

    traces = {}
    with open(path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if "benchmark_name" in entry and "trace_logs" in entry:
                    traces[entry["benchmark_name"]] = entry["trace_logs"]
            except json.JSONDecodeError:
                continue
    return traces

@st.cache_data
def run_forensics(run_id):
    """Runs the forensic analysis engine on a specific run."""
    return analyze_benchmark_run(run_id)

# --- UI Components ---


def render_diff(generated, expected):
    """Renders a side-by-side or unified diff."""
    if not expected:
        st.warning("No expected answer available for comparison.")
        st.code(generated, language="python")
        return

    diff = difflib.unified_diff(
        expected.splitlines(keepends=True),
        generated.splitlines(keepends=True),
        fromfile="Expected",
        tofile="Generated",
    )
    diff_text = "".join(diff)
    if diff_text:
        st.code(diff_text, language="diff")
    else:
        st.success("Answers match perfectly (text-wise).")


def render_logs(logs):
    """Renders trace logs with grouped interactions and filtering."""
    if not logs:
        st.info("No trace logs available.")
        return

    # --- Tool Sequence Summary ---
    tool_sequence = []
    for event in logs:
        if event.get("type") == "tool_use":
            t_name = event.get("tool_name")
            if t_name:
                tool_sequence.append(t_name)
    
    if tool_sequence:
        links = [f"[{t}](#tool-step-{i})" for i, t in enumerate(tool_sequence, 1)]
        st.info(f"**Tool Execution Path:** {' → '.join(links)}")
    else:
        st.caption("No tools were called in this attempt.")

    # Work on a copy to avoid mutating cached data
    logs = list(logs)

    # --- Grouping Logic ---
    grouped_events = []
    i = 0
    while i < len(logs):
        event = logs[i]
        e_type = event.get("type", "unknown")

        # Try to pair tool_use with tool_result
        if e_type == "tool_use":
            # Look ahead for the corresponding result
            result_event = None
            j = i + 1
            while j < len(logs):
                if logs[j].get("type") == "tool_result":
                    result_event = logs[j]
                    logs.pop(j)  # Consume it from our local copy
                    break
                j += 1

            grouped_events.append(
                {
                    "type": "tool_interaction",
                    "tool_use": event,
                    "tool_result": result_event,
                }
            )
        else:
            grouped_events.append(event)

        i += 1

    # --- Filtering ---
    def get_category(event):
        t = event.get("type")
        if t == "tool_interaction":
            return "Tool Interactions"
        if t == "model_response":
            return "Model Responses"
        if t in ["CLI_STDOUT_FULL", "CLI_STDOUT_RAW", "CLI_STDERR"]:
            return "CLI Output"
        if t == "GEMINI_CLIENT_ERROR":
            return "Errors"
        if t == "GEMINI_API_RESPONSE":
            return "API Details"
        return "System Events"

    # Determine available categories in this trace
    available_categories = sorted(list(set(get_category(e) for e in grouped_events)))

    # Default selection: All available categories
    default_categories = available_categories

    selected_categories = st.multiselect(
        "Filter Event Types", options=available_categories, default=default_categories
    )

    # --- Rendering ---
    step_count = 1

    for event in grouped_events:
        cat = get_category(event)
        if cat not in selected_categories:
            continue

        e_type = event.get("type", "unknown")

        # 1. Tool Interaction (Grouped)
        if e_type == "tool_interaction":
            use = event["tool_use"]
            res = event["tool_result"]
            tool_name = use.get("tool_name", "Unknown Tool")

            with st.container(border=True):
                st.markdown(f'<div id="tool-step-{step_count}"></div>', unsafe_allow_html=True)
                st.markdown(f"**Step {step_count}: Tool Call - `{tool_name}`**")

                c_in, c_out = st.columns(2)
                with c_in:
                    with st.expander("Input", expanded=True):
                        st.json(use.get("tool_input"))

                with c_out:
                    if res:
                        with st.expander("Output", expanded=True):
                            st.code(res.get("tool_output"), language="text")
                    else:
                        st.warning("No result recorded.")
            step_count += 1

        # 2. Model Response
        elif e_type == "model_response":
            with st.chat_message("ai"):
                st.write(event.get("content"))

        # 3. CLI Stdout/Stderr
        elif e_type in ["CLI_STDOUT_FULL", "CLI_STDOUT_RAW"]:
            with st.expander(f"📄 CLI Output ({e_type})", expanded=True):
                st.code(event.get("content", ""), language="text")

        elif e_type == "CLI_STDERR":
            with st.expander("⚠️ CLI Stderr (Logs)", expanded=True):
                st.code(event.get("content", ""), language="text")

        # 4. Critical Errors
        elif e_type == "GEMINI_CLIENT_ERROR":
            with st.expander("🚨 Gemini Client Error Report", expanded=True):
                st.error("The Gemini CLI reported an internal error.")
                try:
                    content = event.get("content", "")
                    st.json(json.loads(content))
                except json.JSONDecodeError:
                    st.code(content, language="text")

        # 5. API Response Details
        elif e_type == "GEMINI_API_RESPONSE":
            with st.expander("Gemini API Response Details", expanded=True):
                st.json(event.get("details"))

        # 6. Fallback
        else:
            with st.expander(f"System Event: {e_type}", expanded=True):
                st.json(event)


# --- Error Helper ---

def _get_concise_error_message(row, case_trace_logs) -> str:
    """Extracts a concise error message for display in the header."""
    # Default message
    display_error = "Validation Failed (See 'Validation Error' tab for details)"

    # 1. First, try to extract from the validation_error string itself
    validation_err_str = row.get("validation_error", "")
    captured_report_match = re.search(
        r"\[Captured Error Report\]\n(.*?)(?=\n\n|\[|$)", validation_err_str, re.DOTALL
    )

    if captured_report_match:
        json_content = captured_report_match.group(1).strip()
        try:
            error_json = json.loads(json_content)
            if "error" in error_json and "message" in error_json["error"]:
                return f"❌ Error: {error_json['error']['message']}"
        except json.JSONDecodeError:
            pass  # Fall through to other checks if this JSON is malformed

    # 2. If not found in validation_error, check trace_logs for GEMINI_CLIENT_ERROR
    for log_event in case_trace_logs:
        if log_event.get("type") == "GEMINI_CLIENT_ERROR":
            content = log_event.get("content", {})
            error_json = {}

            if isinstance(content, dict):
                error_json = content
            elif isinstance(content, str):
                try:
                    error_json = json.loads(content)
                except json.JSONDecodeError:
                    pass

            if "error" in error_json and "message" in error_json["error"]:
                return f"❌ Error: {error_json['error']['message']}"

    # If no specific error message found after all checks, return the generic message
    return display_error


def render_tool_analysis(df):
    """Renders the Tool Usage & Impact Analysis section with breakdown options."""
    st.divider()
    st.subheader("🛠️ Tool Usage & Impact Analysis")
    st.markdown("Analysis of tool usage and its correlation with success rates.")
    
    # Define helper early
    def style_lift(v):
        if pd.isna(v): return ""
        if v > 0.0001: return "color: green; font-weight: bold"
        if v < -0.0001: return "color: red; font-weight: bold"
        return "color: gray"

    with st.expander("ℹ️ Methodology & Metrics"):
        st.markdown(
            """
            **1. P(Success | Used)**
            Conditional probability: `Successes / Times Used`.
            
            **2. Baseline Rate (Complement)**
            Probability of success when the specific tool was **NOT** used in the same segment (Generator/Suite).
            `P(Success | NOT Used)`
            This isolates the impact of adding the tool vs. not using it.
            
            **3. Lift**
            `P(Success | Used) - Baseline Rate`.
            - :green[**Positive**]: Tool correlates with higher success compared to non-usage.
            - :red[**Negative**]: Tool correlates with lower success (or is used in hard cases).
            
            **4. Standard Error (SE)**
            Wald interval approximation: `sqrt(p(1-p)/n)`.
            - **High SE (>10%)**: Sample size is too small; estimates are unreliable.
            
            *Note: Each attempt is treated as an independent trial for these calculations.*
            """
        )

    # Breakdown Selection
    breakdown_options = {"Generator": "answer_generator", "Suite": "suite"}
    selected_breakdowns = st.multiselect("Breakdown by", list(breakdown_options.keys()))
    
    group_cols = ["tool"]
    for b in selected_breakdowns:
        group_cols.append(breakdown_options[b])

    tool_stats_data = []
    
    # We iterate over df
    for idx, row in df.iterrows():
        # trace_logs is a list of dicts (from model_dump)
        logs = row.get("trace_logs") or []
        
        # Extract unique tools used in this run
        tools_used = set()
        for log in logs:
            e_type = log.get("type")
            if hasattr(e_type, "value"): e_type = e_type.value # Handle enum if present
            
            if e_type == "tool_use":
                t_name = log.get("tool_name")
                if t_name:
                    tools_used.add(t_name)
        
        is_success = (row["result"] == 1)
        
        # Base entry with breakdown info
        entry_base = {"success": is_success}
        for b_label, b_col in breakdown_options.items():
            entry_base[b_col] = row.get(b_col, "Unknown")

        for tool in tools_used:
            entry = entry_base.copy()
            entry["tool"] = tool
            tool_stats_data.append(entry)
            
    if tool_stats_data:
        df_tools = pd.DataFrame(tool_stats_data)
        
        # 1. Calculate Segment Totals (for Complement Baseline)
        segment_cols = [breakdown_options[b] for b in selected_breakdowns]
        
        if segment_cols:
            segment_stats = df.groupby(segment_cols)["result"].agg(["count", "sum"]).reset_index()
            segment_stats.rename(columns={"count": "segment_total", "sum": "segment_successes"}, inplace=True)
        else:
            # Global stats
            segment_total = len(df)
            segment_successes = df["result"].sum()
        
        # 2. Calculate Tool Stats
        tool_agg = df_tools.groupby(group_cols).agg(
            times_used=("success", "count"),
            successes=("success", "sum")
        ).reset_index()
        
        # 3. Merge Segment Stats
        if segment_cols:
            tool_agg = pd.merge(tool_agg, segment_stats, on=segment_cols, how="left")
        else:
            tool_agg["segment_total"] = segment_total
            tool_agg["segment_successes"] = segment_successes
            
        # 4. Calculate Metrics (Complement Baseline)
        # Complement Count = Total - Used
        tool_agg["complement_count"] = tool_agg["segment_total"] - tool_agg["times_used"]
        tool_agg["complement_successes"] = tool_agg["segment_successes"] - tool_agg["successes"]
        
        # Avoid division by zero
        tool_agg["baseline_pass_rate"] = tool_agg.apply(
            lambda x: x["complement_successes"] / x["complement_count"] if x["complement_count"] > 0 else 0.0, 
            axis=1
        )
        
        tool_agg["pass_rate_val"] = tool_agg["successes"] / tool_agg["times_used"]
        tool_agg["lift_val"] = tool_agg["pass_rate_val"] - tool_agg["baseline_pass_rate"]
        
        # SE
        p = tool_agg["pass_rate_val"]
        n = tool_agg["times_used"]
        tool_agg["se_val"] = (p * (1 - p) / n).pow(0.5)

        # Sort by usage count desc
        tool_agg = tool_agg.sort_values("times_used", ascending=False)
        
        # Rename for display
        tool_agg.rename(columns={
            "pass_rate_val": "Pass Rate",
            "baseline_pass_rate": "Baseline",
            "lift_val": "Lift",
            "se_val": "SE"
        }, inplace=True)
        
        # Select columns
        display_cols = group_cols + ["times_used", "complement_count", "Pass Rate", "SE", "Baseline", "Lift"]
        final_df = tool_agg[display_cols]
        
        col_config = {
            "tool": "Tool Name",
            "times_used": st.column_config.NumberColumn("Times Used", help="Number of benchmark cases where this tool was used at least once."),
            "complement_count": st.column_config.NumberColumn("Baseline (N)", help="Number of runs where this tool was NOT used. Small values (<10) make the Baseline Rate unreliable."),
            "Pass Rate": st.column_config.TextColumn("P(Success | Used)", help="Probability of success given the tool was used."),
            "SE": st.column_config.TextColumn("Std. Error", help="Standard Error."),
            "Baseline": st.column_config.TextColumn("Baseline Rate", help="Average pass rate for this segment (ignoring tool usage)."),
            "Lift": st.column_config.TextColumn("Impact (Lift)", help="Difference vs Baseline."),
        }
        
        for b in selected_breakdowns:
            col_name = breakdown_options[b]
            col_config[col_name] = b

        styler = final_df.style.format({
            "Pass Rate": "{:.1%}",
            "Baseline": "{:.1%}",
            "Lift": "{:+.1%}",
            "SE": "± {:.1%}"
        }).map(style_lift, subset=["Lift"])

        st.dataframe(
            styler,
            use_container_width=True,
            column_config=col_config,
            hide_index=True
        )
    else:
        st.info("No tool usage detected in the trace logs for the current selection.")



# --- Main App ---


def main():
    st.set_page_config(page_title="Benchmark Viewer", layout="wide")
    st.title("📊 ADK Benchmark Viewer")

    # 1. Run Selection (Sidebar)
    runs = load_run_options()
    if not runs:
        st.error("No benchmark runs found in `benchmark_runs/`.")
        return

    selected_run = st.sidebar.selectbox("Select Run", runs)

    if not selected_run:
        return

    # 2. Load Data
    results_list = load_results(selected_run)
    if not results_list:
        st.warning(f"No results found in {selected_run}/results.json. The benchmark run might have failed early or produced no output.")
        return

    # Convert to DataFrame for UI logic
    df = pd.DataFrame([r.model_dump(mode='json') for r in results_list])

    if "suite" in df.columns:
        df["suite"] = df["suite"].apply(
            lambda x: Path(x).parent.name if "/" in x else x
        )

    # 3. Sidebar Filters
    st.sidebar.subheader("Global Filters")
    
    if "suite" in df.columns:
        suites = ["All"] + sorted(df["suite"].unique().tolist())
    else:
        suites = ["All"]
    selected_suite = st.sidebar.selectbox("Filter Suite", suites)

    if "status" in df.columns:
        statuses = ["All"] + sorted(df["status"].unique().tolist())
    else:
        statuses = ["All"]
    selected_status = st.sidebar.selectbox("Filter Status", statuses)
    
    exclude_system_failures = st.sidebar.checkbox("Exclude System Failures", value=False, help="Hides cases with FAIL_SETUP or FAIL_GENERATION status.")

    # 4. Filter Data (Preliminary)
    filtered_df = df.copy()
    if selected_suite != "All" and "suite" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["suite"] == selected_suite]
    if selected_status != "All" and "status" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["status"] == selected_status]
    if exclude_system_failures and "status" in filtered_df.columns:
        filtered_df = filtered_df[~filtered_df["status"].isin([BenchmarkResultType.FAIL_SETUP.value, BenchmarkResultType.FAIL_GENERATION.value])]

    if filtered_df.empty:
        st.info("No data matches the current filters.")
        return

    # 5. Generator Selection (Sidebar)
    st.sidebar.divider()
    st.sidebar.subheader("🤖 Generators")

    # Get generators present in the filtered dataset
    available_generators = sorted(filtered_df["answer_generator"].unique().tolist())

    # Add stats to labels (Pass Rate per generator)
    gen_labels = []
    for gen in available_generators:
        gen_df = filtered_df[filtered_df["answer_generator"] == gen]
        p_count = len(gen_df[gen_df["result"] == 1])
        rate = (p_count / len(gen_df) * 100) if len(gen_df) > 0 else 0
        gen_labels.append(f"{gen} ({rate:.0f}%)")

    # --- Display Selected Generator Description in Sidebar (Above Radio) ---
    # Peek at session state to determine what will likely be selected
    current_idx = st.session_state.get("gen_radio", 0)
    if current_idx >= len(available_generators):
        current_idx = 0
    
    preview_gen = available_generators[current_idx] if available_generators else None

    if preview_gen:
        # Prioritize current runtime description from CANDIDATE_GENERATORS
        gen_desc = next((g.description for g in CANDIDATE_GENERATORS if g.name == preview_gen), None)
        
        if gen_desc:
            with st.sidebar.expander("📝 Generator Description", expanded=True):
                st.markdown(gen_desc)

    selected_gen_index = st.sidebar.radio(
        "Select Generator",
        options=range(len(available_generators)),
        format_func=lambda i: gen_labels[i],
        key="gen_radio",
        label_visibility="collapsed",
    )

    selected_generator = (
        available_generators[selected_gen_index] if available_generators else None
    )

    # 6. Case Selection (Sidebar)
    st.sidebar.divider()
    st.sidebar.subheader("🧪 Cases")

    selected_case_id = None

    if selected_generator:
        # Filter for specific generator
        gen_specific_df = filtered_df[
            filtered_df["answer_generator"] == selected_generator
        ]

        # Sort by Status (Failures first for debugging) then Suite then Name
        gen_specific_df = gen_specific_df.sort_values(
            by=["result", "suite", "benchmark_name"], ascending=[True, True, True]
        )

        case_options = gen_specific_df.index.tolist()

        def format_case_label(idx):
            r = gen_specific_df.loc[idx]
            icon = "✅" if r["result"] == 1 else "❌"
            return f"{icon} [{r['suite']}] {r['benchmark_name']}"

        # Scrollable container in sidebar for cases
        with st.sidebar.container(height=500, border=True):
            if not case_options:
                st.info("No cases found.")
            else:
                # Add explicit Overview and AI Report options
                case_options.insert(0, "AI Report")
                case_options.insert(0, "Overview")

                selected_case_id = st.radio(
                    "Select Case",
                    options=case_options,
                    format_func=lambda x: (
                        "📊 Overview" if x == "Overview" else 
                        "🤖 AI Report" if x == "AI Report" else 
                        format_case_label(x)
                    ),
                    key="case_radio",
                    label_visibility="collapsed",
                )
    else:
        st.sidebar.info("Select a generator first.")



    # 7. Main Area - Dashboard & Details

    if selected_case_id == "Overview":
        # Dashboard Summary (Overview Mode)
        st.header("📊 Global Run Metrics")
        st.markdown(
            "This section provides an overview of the benchmark run's performance, including total cases, filtered cases based on sidebar selections, and the overall pass rate. Metrics are derived from the `results.json` file generated during the benchmark execution."
        )

        crashes_count = len(
            filtered_df[
                filtered_df["status"].isin(
                    [
                        BenchmarkResultType.FAIL_SETUP.value,
                        BenchmarkResultType.FAIL_GENERATION.value,
                    ]
                )
            ]
        )

        col1, col2, col3, col4 = st.columns(4)
        total_runs = len(df)
        filtered_runs = len(filtered_df)
        pass_count = len(filtered_df[filtered_df["result"] == 1])
        pass_rate = (pass_count / filtered_runs * 100) if filtered_runs > 0 else 0

        col1.metric("Total Cases", total_runs)
        col2.metric("Filtered Cases", filtered_runs)
        col3.metric(
            "Accuracy (System Failures = Fail)",
            f"{pass_rate:.1f}%",
            help="Passed / Total. Treats system failures (FAIL_SETUP, FAIL_GENERATION) as failures.",
        )
        col4.metric("System Failures", crashes_count)

        st.divider()
        st.subheader("Detailed Breakdown")
        st.markdown(
            "Metrics are calculated as follows:\n- **Accuracy (System Failures = Fail):** `Passed / Total`. This metric treats any system failure (`FAIL_SETUP`, `FAIL_GENERATION`) as a failure, reflecting the overall system's reliability and correctness.\n- **Accuracy:** `Passed / (Total - System Failures)`. This metric excludes system failures from the total, focusing on the model's performance on valid attempts (i.e., those not encountering setup or generation issues)."
        )

        # 1. Granular Stats (Generator + Suite)
        granular = (
            filtered_df.groupby(["answer_generator", "suite"])
            .agg(
                total=("result", "count"),
                passed=("result", "sum"),
                system_failures=(
                    "status",
                    lambda x: (
                        x.isin(
                            [
                                BenchmarkResultType.FAIL_SETUP.value,
                                BenchmarkResultType.FAIL_GENERATION.value,
                            ]
                        )
                    ).sum(),
                ),
            )
            .reset_index()
        )

        # 2. Aggregate Stats (Generator only)
        aggregate = (
            filtered_df.groupby("answer_generator")
            .agg(
                total=("result", "count"),
                passed=("result", "sum"),
                system_failures=(
                    "status",
                    lambda x: (
                        x.isin(
                            [
                                BenchmarkResultType.FAIL_SETUP.value,
                                BenchmarkResultType.FAIL_GENERATION.value,
                            ]
                        )
                    ).sum(),
                ),
            )
            .reset_index()
        )
        aggregate["suite"] = " (All Suites)"

        # 3. Combine & Calculate Metrics
        unified = pd.concat([aggregate, granular], ignore_index=True)

        unified["valid_attempts"] = unified["total"] - unified["system_failures"]
        unified["Accuracy (System Failures = Fail)"] = (
            unified["passed"] / unified["total"] * 100
        )
        unified["Accuracy"] = unified.apply(
            lambda r: (
                (r["passed"] / r["valid_attempts"] * 100)
                if r["valid_attempts"] > 0
                else 0.0
            ),
            axis=1,
        )

        # 4. Format
        unified["Accuracy (System Failures = Fail)"] = unified[
            "Accuracy (System Failures = Fail)"
        ].map("{:.1f}%".format)
        unified["Accuracy"] = unified["Accuracy"].map("{:.1f}%".format)

        # 5. Sort (Generator, then Suite with (All Suites) first)
        unified = unified.sort_values(by=["answer_generator", "suite"])

        st.dataframe(
            unified[
                [
                    "answer_generator",
                    "suite",
                    "passed",
                    "system_failures",
                    "total",
                    "Accuracy (System Failures = Fail)",
                    "Accuracy",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "answer_generator": "Generator",
                "suite": "Suite",
                "passed": "Passed",
                "system_failures": "System Failures",
                "total": "Total",
                "Accuracy (System Failures = Fail)": st.column_config.TextColumn(
                    "Accuracy (System Failures = Fail)",
                    help="Passed / Total. Treats system failures (FAIL_SETUP, FAIL_GENERATION) as failures.",
                ),
                "Accuracy": st.column_config.TextColumn(
                    "Accuracy",
                    help="Passed / (Total - System Failures). Ignores system failures to measure model intelligence on valid attempts.",
                ),
            },
        )

        # 6. API Key Analysis
        st.divider()
        st.subheader("🔑 API Key Error Analysis")
        st.markdown("Breakdown of errors and pass rates by API Key ID.")

        # Expand all attempts into a flat list for analysis
        attempts_data = []
        for _, row in filtered_df.iterrows():
            attempts = row.get("generation_attempts")
            if not isinstance(attempts, list):
                continue

            for att in attempts:
                if isinstance(att, dict):
                    attempts_data.append(
                        {
                            "key_id": att.get("api_key_id", "Unknown"),
                            "status": att.get("status", "unknown"),
                            "error": att.get("error_message") or "",
                            "suite": row["suite"],
                            "generator": row["answer_generator"],
                        }
                    )

        if attempts_data:
            df_attempts = pd.DataFrame(attempts_data)

            # Aggregate by Key ID
            key_stats = (
                df_attempts.groupby("key_id")
                .agg(
                    total_attempts=("status", "count"),
                    successes=("status", lambda x: (x == "success").sum()),
                    failures=("status", lambda x: (x == "failure").sum()),
                )
                .reset_index()
            )

            key_stats["Failure Rate"] = (
                key_stats["failures"] / key_stats["total_attempts"] * 100
            ).map("{:.1f}%".format)

            st.dataframe(
                key_stats,
                use_container_width=True,
                column_config={
                    "key_id": "API Key ID",
                    "total_attempts": "Attempts",
                    "successes": "Successes",
                    "failures": "Failures",
                },
            )

            with st.expander("View Error Details by Key"):
                failed_attempts = df_attempts[df_attempts["status"] == "failure"]
                if not failed_attempts.empty:
                    st.dataframe(
                        failed_attempts[[ "key_id", "suite", "generator", "error"]],
                        use_container_width=True,
                    )
                else:
                    st.success("No failed attempts found in the selected filter range.")
        else:
            st.info("No generation attempt history found in this dataset.")

        # 7. Forensic Analysis Integration
        st.divider()
        st.subheader("🕵️ Forensic Diagnosis")
        
        if st.button("Run Deep Forensic Scan"):
            with st.spinner("Analyzing trace logs..."):
                run_analysis = run_forensics(selected_run)
                
                if run_analysis.total_failures == 0:
                    st.success("No failures detected in this run to analyze!")
                else:
                    # Categories
                    from collections import Counter
                    all_failed_cases = [c for c in run_analysis.cases if c.result_score == 0]
                    cats = Counter([c.primary_failure_category for c in all_failed_cases])
                    
                    # Heuristics
                    alerts = run_analysis.get_critical_alerts()
                    hallucinations = sum(1 for a in alerts if "Sanitizer Hallucination" in a["reasons"])
                    loop_kills = sum(1 for a in alerts if "Early Loop Exit" in a["reasons"])
                    
                    # Layout
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Analyzed Cases", len(run_analysis.cases))
                    c2.metric("Critical Hallucinations", hallucinations, delta=-hallucinations if hallucinations > 0 else 0, delta_color="inverse")
                    c3.metric("Early Loop Exits", loop_kills, delta=-loop_kills if loop_kills > 0 else 0, delta_color="inverse")
                    
                    st.write("**Top Failure Categories:**")
                    cat_df = pd.DataFrame(cats.most_common(), columns=["Category", "Count"])
                    st.dataframe(cat_df, use_container_width=True, hide_index=True)
                    
                    with st.expander("View Detailed Forensic Report"):
                        for c in all_failed_cases:
                            icon = "⚠️" if c.has_critical_heuristic_failure else "❌"
                            st.markdown(f"**{icon} {c.benchmark_name}**")
                            st.caption(f"Error: {c.primary_failure_category}")
                            
                            for i, att in enumerate(c.attempts):
                                if len(c.attempts) > 1:
                                    st.write(f"Attempt {i+1}")
                                st.json(att.__dict__) # Dump analysis stats
                            st.divider()

    elif selected_case_id == "AI Report":
        st.header("🤖 AI Analysis Report")
        report_path = BENCHMARK_RUNS_DIR / selected_run / "log_analysis.md"
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as f:
                st.markdown(f.read())
        else:
            st.warning(f"No AI analysis report found for this run at `{report_path}`. Run the Log Analyzer to generate one.")

    # 7. Tool Usage Analysis
    if selected_case_id == "Overview" or selected_case_id == "AI Report" or selected_case_id is None:
        render_tool_analysis(filtered_df)


    if selected_case_id is not None and selected_case_id not in ["Overview", "AI Report"]:
        # Use typed object for detail view
        result_obj = results_list[selected_case_id]
        generation_attempts = result_obj.generation_attempts or []

        # Header Info (Global for the case)
        h1, h2, h3 = st.columns([3, 1, 1])
        h1.markdown(f"#### {result_obj.benchmark_name}")
        
        total_tokens = "N/A"
        if result_obj.usage_metadata and result_obj.usage_metadata.total_tokens is not None:
            total_tokens = result_obj.usage_metadata.total_tokens
            
        h2.caption(f"Latency: {result_obj.latency:.4f}s | Tokens: {total_tokens}")
        h3.caption(
            f"Total Attempts: {len(generation_attempts)}"
        )

        # Prioritize current runtime description from CANDIDATE_GENERATORS
        gen_desc = next((g.description for g in CANDIDATE_GENERATORS if g.name == result_obj.answer_generator), None)
        if not gen_desc:
            gen_desc = result_obj.generator_description

        if gen_desc:
            with st.expander(f"Generator: {result_obj.answer_generator}", expanded=False):
                st.markdown(gen_desc)

        # Display explicit global case status
        status_color = "green" if result_obj.result == 1 else "red"
        st.markdown(f"Final Status: :{status_color}[**{result_obj.status.value.upper()}**]")

        if result_obj.validation_error:
            if result_obj.result == 1:
                st.warning(f"**Validation Warning (Final):** {result_obj.validation_error}")
            else:
                st.error(_get_concise_error_message(result_obj.model_dump(), [t.model_dump() for t in (result_obj.trace_logs or [])]))
        elif result_obj.result == 1:
            st.success("**Validation Passed (Final)**")

        st.divider()

        # --- Tabs for Attempts (Overview + Individual Attempts) ---
        tab_names = ["Run Overview"] + [f"Attempt {att.attempt_number}" for att in generation_attempts]
        main_tabs = st.tabs(tab_names)

        # Tab 0: Run Overview (Summary Table)
        with main_tabs[0]:
            st.subheader("Generation Attempts Overview")
            if generation_attempts:
                history_data = []
                for att in generation_attempts:
                    is_success = att.status == "success"
                    icon = "✅" if is_success else "❌"
                    status_display = "Completed" if is_success else "Failed"
                    
                    att_usage = att.usage_metadata
                    tokens = att_usage.total_tokens if att_usage else "N/A"
                    
                    history_data.append({
                        "Attempt": f"{icon} {att.attempt_number}",
                        "Status": status_display,
                        "Duration": f"{att.duration:.2f}s",
                        "Tokens": str(tokens),
                        "Error": att.error_message or "-"
                    })
                
                df_history = pd.DataFrame(history_data)
                st.dataframe(
                    df_history, 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Error": st.column_config.TextColumn("Error", width="large"),
                        "Tokens": st.column_config.TextColumn("Tokens", help="Token usage for this specific attempt. Includes cost of failed runs for debugging.")
                    }
                )
            else:
                st.info("No detailed attempt history available.")

        # Tab 1..N: Individual Attempts
        for i, attempt in enumerate(generation_attempts):
            with main_tabs[i+1]:
                st.markdown(f"### Details for Attempt {attempt.attempt_number}")
                
                # Context variables for this attempt
                active_trace_logs = attempt.trace_logs or []
                active_answer = attempt.answer or ""
                active_usage = attempt.usage_metadata
                
                total_tokens = active_usage.total_tokens if active_usage else "N/A"
                # Safe access thanks to default_factory=dict
                loop_exit = active_usage.extra_tags.get("loop_exit_reason") if active_usage else None
                exit_str = f" | Exit: {loop_exit}" if loop_exit else ""
                
                st.caption(f"Generation Status: {attempt.status} | Duration: {attempt.duration:.2f}s | Tokens: {total_tokens}{exit_str}")

                # Nested Tabs for deep dive
                sub_tabs = st.tabs(["Diff & Code", "Trace Logs", "Raw Events", "Generation Error", "Validation Error", "Metadata"])
                
                # 1. Diff & Code
                with sub_tabs[0]:
                    st.markdown("#### Generated Code vs Ground Truth")
                    st.markdown("Compares the generated answer against the ground truth.")
                    selected_code = str(active_answer)
                    view_mode = st.radio("Diff View", ["Side-by-Side", "Unified Diff", "Original (Unfixed)"], horizontal=True, key=f"diff_mode_{i}")
                    
                    if view_mode == "Side-by-Side":
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            st.caption("Generated Answer")
                            if selected_code:
                                st.code(selected_code, language="python")
                            else:
                                st.info("No answer produced for this attempt.")
                        with sc2:
                            st.caption("Ground Truth")
                            st.code(result_obj.ground_truth or "", language="python")
                    elif view_mode == "Unified Diff":
                        st.caption(f"Unified Diff (Attempt {attempt.attempt_number} vs Ground Truth)")
                        render_diff(selected_code, str(result_obj.ground_truth or ""))
                    else:
                        st.caption("Original (Unfixed) Code")
                        if result_obj.unfixed_code:
                            st.code(result_obj.unfixed_code, language="python")
                        else:
                            st.info("Original (unfixed) code is not available for this benchmark type or was not recorded.")

                # 2. Trace Logs
                with sub_tabs[1]:
                    st.markdown("#### Attempt Trace Logs")
                    st.markdown("Chronological trace of tool calls, model responses, and CLI outputs.")
                    if not active_trace_logs:
                        st.warning("No trace logs available for this attempt. Logs are typically recorded only when the generation phase successfully produces an answer.")
                    else:
                        render_logs([t.model_dump() for t in active_trace_logs])

                # 3. Raw Events
                with sub_tabs[2]:
                    st.markdown("#### Raw ADK Events for Attempt")
                    st.markdown("Raw JSON event objects captured from the runner.")
                    if not active_trace_logs:
                        st.warning("No raw events available for this attempt. Raw events are typically recorded only when the generation phase successfully produces an answer.")
                    else:
                        st.json([t.model_dump() for t in active_trace_logs])

                # 4. Generation Error
                with sub_tabs[3]:
                    st.markdown("#### Generation Error Details")
                    st.markdown("Error details if the attempt failed to produce an answer.")
                    if attempt.status != "success":
                        st.error(f"Generation of answer failed: {attempt.error_message}")
                    else:
                        st.info("Generation successful for this attempt.")
                
                # 5. Validation Error (Global for the case)
                with sub_tabs[4]:
                    st.markdown("#### Overall Case Validation Error")
                    st.markdown("Global validation result for the benchmark case.")
                    if result_obj.validation_error:
                        st.error(f"Validation failed for the overall case: {result_obj.validation_error}")
                    else:
                        st.success("Overall case validation passed.")

                # 6. Metadata
                with sub_tabs[5]:
                    st.markdown("#### Attempt Metadata")
                    st.markdown("Token usage and other execution metadata.")
                    st.caption("Note: Top-level statistics (header) typically reflect the final successful attempt. Usage for failed attempts is visible in the 'Run Overview'.")
                    if active_usage:
                        st.json(active_usage.model_dump())
                        if active_usage.extra_tags:
                            st.write("**Extra Tags:**")
                            st.json(active_usage.extra_tags)
                    else:
                        st.info("No usage metadata for this attempt.")
                    
                    with st.expander("Raw Result Data (Global Case Data)"):
                        st.json(result_obj.model_dump())

    elif selected_case_id is None:
        st.info("Select a case from the sidebar to view details.")


if __name__ == "__main__":
    main()