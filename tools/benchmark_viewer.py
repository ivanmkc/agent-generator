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
        st.text(diff_text)
    else:
        st.success("Answers match perfectly (text-wise).")

def render_logs(logs):
    """Renders trace logs with special handling for stdout."""
    if not logs:
        st.info("No trace logs available.")
        return

    for event in logs:
        e_type = event.get("type", "unknown")
        
        if e_type == "CLI_STDOUT_FULL":
            with st.expander("📄 Full CLI Stdout (Raw)", expanded=False):
                st.code(event.get("content", ""), language="text")
        
        elif e_type == "CLI_STDERR":
            st.error(f"Stderr: {event.get('content', '')}")
            
        elif e_type == "tool_use":
            with st.chat_message("ai", avatar="🛠️"):
                st.write(f"**Tool Call:** `{event.get('tool_name')}`")
                st.json(event.get('tool_input'))
        
        elif e_type == "tool_result":
            with st.chat_message("human", avatar="📦"):
                st.write("**Tool Result:**")
                st.code(event.get('tool_output'))
        
        elif e_type == "model_response":
             with st.chat_message("ai"):
                 st.write(event.get("content"))
        
        elif e_type == "GEMINI_API_RESPONSE":
             with st.expander("Gemini API Response Details"):
                 st.json(event.get("details"))
        
        else:
            with st.expander(f"Event: {e_type}"):
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
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Generated Answer")
                st.code(row["answer"], language="python")
            with c2:
                st.caption("Ground Truth")
                st.code(row.get("ground_truth", ""), language="python")
            
            st.caption("Unified Diff")
            render_diff(str(row["answer"]), str(row.get("ground_truth", "")))

        with tab_logs:
            logs = row.get("trace_logs")
            if not logs:
                st.warning("Trace logs not found in results.json.")
            render_logs(logs)

        with tab_meta:
            st.json(row.get("usage_metadata"))
            with st.expander("Raw Result Data"):
                st.json(row.to_dict())
    else:
        st.info("Select a case from the sidebar to view details.")

if __name__ == "__main__":
    main()