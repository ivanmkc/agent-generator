import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
import difflib
import re
from benchmarks.data_models import BenchmarkResultType

# --- Constants ---
BENCHMARK_RUNS_DIR = Path("benchmark_runs")

# --- Helper Functions ---

def load_run_options():
    """Returns a list of available benchmark run directories (timestamps), sorted newest first."""
    if not BENCHMARK_RUNS_DIR.exists():
        return []
    runs = [d.name for d in BENCHMARK_RUNS_DIR.iterdir() if d.is_dir()]
    runs.sort(reverse=True)
    return runs

@st.cache_data
def load_results(run_id):
    """Loads results.json for a given run ID into a DataFrame."""
    path = BENCHMARK_RUNS_DIR / run_id / "results.json"
    if not path.exists():
        return None
    
    with open(path, "r") as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    if "suite" in df.columns:
        df["suite"] = df["suite"].apply(lambda x: Path(x).parent.name if "/" in x else x)
    
    return df

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
            if not line.strip(): continue
            try:
                entry = json.loads(line)
                if "benchmark_name" in entry and "trace_logs" in entry:
                    traces[entry["benchmark_name"]] = entry["trace_logs"]
            except json.JSONDecodeError:
                continue
    return traces

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
                    logs.pop(j) # Consume it from our local copy
                    break
                j += 1
            
            grouped_events.append({
                "type": "tool_interaction",
                "tool_use": event,
                "tool_result": result_event
            })
        else:
            grouped_events.append(event)
        
        i += 1

    # --- Filtering ---
    def get_category(event):
        t = event.get("type")
        if t == "tool_interaction": return "Tool Interactions"
        if t == "model_response": return "Model Responses"
        if t in ["CLI_STDOUT_FULL", "CLI_STDOUT_RAW", "CLI_STDERR"]: return "CLI Output"
        if t == "GEMINI_CLIENT_ERROR": return "Errors"
        if t == "GEMINI_API_RESPONSE": return "API Details"
        return "System Events"

    # Determine available categories in this trace
    available_categories = sorted(list(set(get_category(e) for e in grouped_events)))
    
    # Default selection: All available categories
    default_categories = available_categories

    selected_categories = st.multiselect(
        "Filter Event Types",
        options=available_categories,
        default=default_categories
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

# --- Main App ---

def _get_concise_error_message(row, case_trace_logs) -> str:
    """Extracts a concise error message for display in the header."""
    # Default message
    display_error = "Validation Failed (See 'Validation Error' tab for details)"
    
    # 1. First, try to extract from the validation_error string itself
    validation_err_str = row.get("validation_error", "")
    captured_report_match = re.search(r"\[Captured Error Report\]\n(.*?)(?=\n\n|\[|$)", validation_err_str, re.DOTALL)
    
    if captured_report_match:
        json_content = captured_report_match.group(1).strip()
        try:
            error_json = json.loads(json_content)
            if "error" in error_json and "message" in error_json["error"]:
                return f"❌ Error: {error_json['error']['message']}"
        except json.JSONDecodeError:
            pass # Fall through to other checks if this JSON is malformed

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
    df = load_results(selected_run)
    if df is None:
        st.error(f"Could not load results.json for {selected_run}")
        return

    # 3. Sidebar Filters
    st.sidebar.subheader("Global Filters")
    suites = ["All"] + sorted(df["suite"].unique().tolist())
    selected_suite = st.sidebar.selectbox("Filter Suite", suites)
    
    statuses = ["All"] + sorted(df["status"].unique().tolist())
    selected_status = st.sidebar.selectbox("Filter Status", statuses)

    # 4. Filter Data (Preliminary)
    filtered_df = df.copy()
    if selected_suite != "All":
        filtered_df = filtered_df[filtered_df["suite"] == selected_suite]
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]

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
    
    selected_gen_index = st.sidebar.radio(
        "Select Generator",
        options=range(len(available_generators)),
        format_func=lambda i: gen_labels[i],
        key="gen_radio",
        label_visibility="collapsed"
    )
    
    selected_generator = available_generators[selected_gen_index] if available_generators else None

    # 6. Case Selection (Sidebar)
    st.sidebar.divider()
    st.sidebar.subheader("🧪 Cases")
    
    selected_case_id = None
    
    if selected_generator:
        # Filter for specific generator
        gen_specific_df = filtered_df[filtered_df["answer_generator"] == selected_generator]
        
        # Sort by Status (Failures first for debugging) then Suite then Name
        gen_specific_df = gen_specific_df.sort_values(
            by=["result", "suite", "benchmark_name"], 
            ascending=[True, True, True] 
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
                # Add explicit Overview option
                case_options.insert(0, "Overview")
                
                selected_case_id = st.radio(
                    "Select Case",
                    options=case_options,
                    format_func=lambda x: "📊 Overview" if x == "Overview" else format_case_label(x),
                    key="case_radio",
                    label_visibility="collapsed"
                )
    else:
        st.sidebar.info("Select a generator first.")


    # 7. Main Area - Dashboard & Details
    
    if selected_case_id == "Overview":
        # Dashboard Summary (Overview Mode)
        st.header("📊 Global Run Metrics")
        st.markdown("This section provides an overview of the benchmark run's performance, including total cases, filtered cases based on sidebar selections, and the overall pass rate. Metrics are derived from the `results.json` file generated during the benchmark execution.")
        
        crashes_count = len(filtered_df[filtered_df["status"].isin([BenchmarkResultType.FAIL_SETUP.value, BenchmarkResultType.FAIL_GENERATION.value])])
        
        col1, col2, col3, col4 = st.columns(4)
        total_runs = len(df)
        filtered_runs = len(filtered_df)
        pass_count = len(filtered_df[filtered_df["result"] == 1])
        pass_rate = (pass_count / filtered_runs * 100) if filtered_runs > 0 else 0
        
        col1.metric("Total Cases", total_runs)
        col2.metric("Filtered Cases", filtered_runs)
        col3.metric("Accuracy (System Failures = Fail)", f"{pass_rate:.1f}%", help="Passed / Total. Treats system failures (FAIL_SETUP, FAIL_GENERATION) as failures.")
        col4.metric("System Failures", crashes_count)

        st.divider()
        st.subheader("Detailed Breakdown")
        st.markdown("Metrics are calculated as follows:\n- **Accuracy (System Failures = Fail):** `Passed / Total`. This metric treats any system failure (`FAIL_SETUP`, `FAIL_GENERATION`) as a failure, reflecting the overall system's reliability and correctness.\n- **Accuracy:** `Passed / (Total - System Failures)`. This metric excludes system failures from the total, focusing on the model's performance on valid attempts (i.e., those not encountering setup or generation issues).")

        # 1. Granular Stats (Generator + Suite)
        granular = filtered_df.groupby(["answer_generator", "suite"]).agg(
            total=("result", "count"),
            passed=("result", "sum"),
            system_failures=("status", lambda x: (x.isin([BenchmarkResultType.FAIL_SETUP.value, BenchmarkResultType.FAIL_GENERATION.value])).sum())
        ).reset_index()

        # 2. Aggregate Stats (Generator only)
        aggregate = filtered_df.groupby("answer_generator").agg(
            total=("result", "count"),
            passed=("result", "sum"),
            system_failures=("status", lambda x: (x.isin([BenchmarkResultType.FAIL_SETUP.value, BenchmarkResultType.FAIL_GENERATION.value])).sum())
        ).reset_index()
        aggregate["suite"] = " (All Suites)"

        # 3. Combine & Calculate Metrics
        unified = pd.concat([aggregate, granular], ignore_index=True)
        
        unified["valid_attempts"] = unified["total"] - unified["system_failures"]
        unified["Accuracy (System Failures = Fail)"] = (unified["passed"] / unified["total"] * 100)
        unified["Accuracy"] = unified.apply(
            lambda r: (r["passed"] / r["valid_attempts"] * 100) if r["valid_attempts"] > 0 else 0.0, axis=1
        )
        
        # 4. Format
        unified["Accuracy (System Failures = Fail)"] = unified["Accuracy (System Failures = Fail)"].map("{:.1f}%".format)
        unified["Accuracy"] = unified["Accuracy"].map("{:.1f}%".format)
        
        # 5. Sort (Generator, then Suite with (All Suites) first)
        unified = unified.sort_values(by=["answer_generator", "suite"])
        
        st.dataframe(
            unified[["answer_generator", "suite", "passed", "system_failures", "total", "Accuracy (System Failures = Fail)", "Accuracy"]],
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
                    help="Passed / Total. Treats system failures (FAIL_SETUP, FAIL_GENERATION) as failures."
                ),
                "Accuracy": st.column_config.TextColumn(
                    "Accuracy",
                    help="Passed / (Total - System Failures). Ignores system failures to measure model intelligence on valid attempts."
                ),
            }
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
                # If no attempts recorded (legacy), try to infer from single result if we had key info there?
                # Currently we don't have api_key_id in top level BenchmarkRunResult, only in GeneratedAnswer (which isn't preserved directly except via answer/logs)
                # But wait, we added generation_attempts to BenchmarkRunResult, so it should be there.
                continue
                
            for att in attempts:
                if isinstance(att, dict):
                    attempts_data.append({
                        "key_id": att.get("api_key_id", "Unknown"),
                        "status": att.get("status", "unknown"),
                        "error": att.get("error_message") or "",
                        "suite": row["suite"],
                        "generator": row["answer_generator"]
                    })
        
        if attempts_data:
            df_attempts = pd.DataFrame(attempts_data)
            
            # Aggregate by Key ID
            key_stats = df_attempts.groupby("key_id").agg(
                total_attempts=("status", "count"),
                successes=("status", lambda x: (x == "success").sum()),
                failures=("status", lambda x: (x == "failure").sum())
            ).reset_index()
            
            key_stats["Failure Rate"] = (key_stats["failures"] / key_stats["total_attempts"] * 100).map("{:.1f}%".format)
            
            st.dataframe(
                key_stats, 
                use_container_width=True,
                column_config={
                    "key_id": "API Key ID",
                    "total_attempts": "Attempts",
                    "successes": "Successes",
                    "failures": "Failures"
                }
            )
            
            with st.expander("View Error Details by Key"):
                failed_attempts = df_attempts[df_attempts["status"] == "failure"]
                if not failed_attempts.empty:
                    st.dataframe(failed_attempts[["key_id", "suite", "generator", "error"]], use_container_width=True)
                else:
                    st.success("No failed attempts found in the selected filter range.")
        else:
            st.info("No generation attempt history found in this dataset.")

    if selected_case_id is not None and selected_case_id != "Overview":
        row = filtered_df.loc[selected_case_id]
        case_trace_logs = row.get("trace_logs", []) or []
        generation_attempts = row.get("generation_attempts", []) or []

        # Header Info
        h1, h2, h3 = st.columns([3, 1, 1])
        h1.markdown(f"#### {row['benchmark_name']}")
        h2.caption(f"Latency: {row['latency']:.4f}s")
        h3.caption(f"Attempts: {len(generation_attempts) if generation_attempts else 'N/A'}")
        
        # Display explicit status
        status_color = "green" if row['result'] == 1 else "red"
        st.markdown(f"Status: :{status_color}[**{row['status'].upper()}**]")

        if row['validation_error']:
            if row['result'] == 1:
                st.warning(f"**Validation Warning:** {row['validation_error']}")
            else:
                st.error(_get_concise_error_message(row, case_trace_logs))
        elif row['result'] == 1:
            st.success("**Passed**")

        # Tabs for deep dive
        tab_history, tab_answer, tab_logs, tab_error, tab_meta = st.tabs(["Retry History", "Diff & Code", "Trace Logs", "Validation Error", "Metadata"])
        
        with tab_history:
            st.markdown("### Generation Attempts History")
            if generation_attempts:
                for att in generation_attempts:
                    # att is a dict if loaded from JSON
                    is_success = att.get("status") == "success"
                    icon = "✅" if is_success else "❌"
                    with st.expander(f"{icon} Attempt {att.get('attempt_number')} (Key: {att.get('api_key_id', 'Unknown')})", expanded=not is_success):
                        c1, c2 = st.columns(2)
                        c1.metric("Duration", f"{att.get('duration', 0):.2f}s")
                        c2.metric("Status", att.get("status"))
                        if not is_success:
                            st.error(f"Error: {att.get('error_message')}")
            else:
                st.info("No detailed attempt history available for this run.")

        with tab_answer:
            st.markdown("This section compares the `Generated Answer` from the agent against the `Ground Truth` (expected answer) defined in the benchmark. You can toggle between a side-by-side view of the full code/text and a colored unified diff that highlights changes.")
            
            # Attempt Selection
            selected_code = str(row["answer"])
            diff_label = "Final Answer"
            
            # Check for legacy extracted attempts from logs (fallback)
            legacy_attempts = []
            for i, event in enumerate(case_trace_logs):
                if event.get("type") == "tool_use" and event.get("tool_name") == "write_file":
                    content = event.get("tool_input", {}).get("content")
                    if content:
                        legacy_attempts.append({
                            "step": i + 1,
                            "code": content,
                            "label": f"Log Step {i + 1}"
                        })

            if legacy_attempts:
                options = ["Final Result"] + [a["label"] for a in legacy_attempts]
                selection = st.selectbox("Select Code Version", options)
                
                if selection != "Final Result":
                    for a in legacy_attempts:
                        if a["label"] == selection:
                            selected_code = a["code"]
                            diff_label = selection
                            break
            
            view_mode = st.radio("Diff View", ["Side-by-Side", "Unified Diff"], horizontal=True)

            if view_mode == "Side-by-Side":
                c1, c2 = st.columns(2)
                with c1:
                    st.caption(f"Generated ({diff_label})")
                    st.code(selected_code, language="python")
                with c2:
                    st.caption("Ground Truth")
                    st.code(row.get("ground_truth", ""), language="python")
            else:
                st.caption(f"Unified Diff ({diff_label} vs Ground Truth)")
                render_diff(selected_code, str(row.get("ground_truth") or ""))

        with tab_logs:
            st.markdown("This tab displays a chronological trace of events that occurred during the agent's execution for this benchmark case. It includes tool calls, their results, raw CLI outputs, and any captured errors, providing a detailed understanding of the agent's decision-making process.")
            if not case_trace_logs:
                st.warning("Trace logs not found in results.json.")
            render_logs(case_trace_logs)

        with tab_error:
            if row['validation_error']:
                st.markdown("### Validation Error Details")
                st.text(row['validation_error'])
            else:
                st.info("No validation errors recorded.")
            
            # Debug: Show any GEMINI_CLIENT_ERROR found in logs
            client_errors = [e for e in case_trace_logs if e.get("type") == "GEMINI_CLIENT_ERROR"]
            if client_errors:
                st.divider()
                st.markdown("### 🐞 Debug: Client Errors in Logs")
                for i, err in enumerate(client_errors):
                    st.markdown(f"**Error Event {i+1} Raw Content:**")
                    st.json(err)

        with tab_meta:
            st.markdown("This section provides additional metadata about the benchmark case execution, including API usage, model details, latency, and raw result data from `results.json`.")
            st.json(row.get("usage_metadata"))
            with st.expander("Raw Result Data"):
                st.json(row.to_dict())
    elif selected_case_id is None:
        st.info("Select a case from the sidebar to view details.")

if __name__ == "__main__":
    main()