import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
import difflib

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
    
    # Default selection: The most relevant narrative elements
    default_categories = [c for c in available_categories if c in ["Tool Interactions", "Model Responses", "Errors"]]
    if not default_categories:
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
            with st.expander("⚠️ CLI Stderr", expanded=True):
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
                selected_case_id = st.radio(
                    "Select Case",
                    options=case_options,
                    format_func=format_case_label,
                    key="case_radio",
                    label_visibility="collapsed"
                )
    else:
        st.sidebar.info("Select a generator first.")


    # 7. Main Area - Dashboard & Details
    # Dashboard Summary
    with st.expander("📊 Global Run Metrics", expanded=False):
        st.markdown("This section provides an overview of the benchmark run's performance, including total cases, filtered cases based on sidebar selections, and the overall pass rate. Metrics are derived from the `results.json` file generated during the benchmark execution.")
        col1, col2, col3 = st.columns(3)
        total_runs = len(df)
        filtered_runs = len(filtered_df)
        pass_count = len(filtered_df[filtered_df["result"] == 1])
        pass_rate = (pass_count / filtered_runs * 100) if filtered_runs > 0 else 0
        
        col1.metric("Total Cases", total_runs)
        col2.metric("Filtered Cases", filtered_runs)
        col3.metric("Pass Rate (Filtered)", f"{pass_rate:.1f}%")

    st.divider()

    # Detail View
    st.markdown("### 📝 Details")
    st.markdown("Dive deeper into individual benchmark cases. Select a case from the sidebar to view its generated answer, comparison with ground truth, detailed trace logs, and execution metadata.")
    
    if selected_case_id is not None:
        row = filtered_df.loc[selected_case_id]
        
        # Header Info
        h1, h2 = st.columns([3, 1])
        h1.markdown(f"#### {row['benchmark_name']}")
        h2.caption(f"Latency: {row['latency']:.4f}s")
        
        if row['validation_error']:
            st.error(f"**Error:** {row['validation_error']}")
        elif row['result'] == 1:
            st.success("**Passed**")

        # Tabs for deep dive
        tab_answer, tab_logs, tab_meta = st.tabs(["Diff & Code", "Trace Logs", "Metadata"])
        
        with tab_answer:
            st.markdown("This section compares the `Generated Answer` from the agent against the `Ground Truth` (expected answer) defined in the benchmark. You can toggle between a side-by-side view of the full code/text and a colored unified diff that highlights changes.")
            view_mode = st.radio("Diff View", ["Side-by-Side", "Unified Diff"], horizontal=True)

            if view_mode == "Side-by-Side":
                c1, c2 = st.columns(2)
                with c1:
                    st.caption("Generated Answer")
                    st.code(row["answer"], language="python")
                with c2:
                    st.caption("Ground Truth")
                    st.code(row.get("ground_truth", ""), language="python")
            else:
                st.caption("Unified Diff")
                render_diff(str(row["answer"]), str(row.get("ground_truth", "")))

        with tab_logs:
            st.markdown("This tab displays a chronological trace of events that occurred during the agent's execution for this benchmark case. It includes tool calls, their results, raw CLI outputs, and any captured errors, providing a detailed understanding of the agent's decision-making process.")
            logs = row.get("trace_logs")
            if not logs:
                st.warning("Trace logs not found in results.json.")
            render_logs(logs)

        with tab_meta:
            st.markdown("This section provides additional metadata about the benchmark case execution, including API usage, model details, latency, and raw result data from `results.json`.")
            st.json(row.get("usage_metadata"))
            with st.expander("Raw Result Data"):
                st.json(row.to_dict())
    else:
        st.info("Select a case from the sidebar to view details.")

if __name__ == "__main__":
    main()