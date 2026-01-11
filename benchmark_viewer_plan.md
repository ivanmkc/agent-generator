# Benchmark Viewer Web App Plan

## Objective
Create a lightweight, locally hosted web application to visualize and debug benchmark results stored in the `benchmark_runs/` directory.

## Core Features
1.  **Run Selection**: Browse and select specific benchmark runs (timestamped folders).
2.  **Dashboard**: View high-level metrics (Pass Rate, Total Runs, Failures) for the selected run.
3.  **Case Explorer**: Filter and list individual benchmark cases.
4.  **Deep Dive**: Inspect specific case details:
    - Status (Pass/Fail/Crash)
    - Generated Answer vs. Expected Answer (Diff view)
    - **Full Trace Logs**: View raw `stdout`, stderr, and tool calls.

## Technical Architecture

**Framework:** [Streamlit](https://streamlit.io/)
*   **Why?** It allows building interactive data apps purely in Python. No separate frontend (React/HTML) required. It natively supports dataframes, charts, and text rendering, making it ideal for this use case.

**File Structure:**
- `tools/benchmark_viewer.py`: The main Streamlit application script.

## Implementation Steps

### 1. Setup
- Add `streamlit` to `requirements.txt`.
- Create `tools/` directory if it doesn't exist.

### 2. Data Loading (`tools/benchmark_viewer.py`)
- Implement a function to list directories in `benchmark_runs/` sorted by date (newest first).
- Implement a function to load `results.json` for a selected run into a Pandas DataFrame.
- Implement a function to load/parse `trace.jsonl` (lazy loading or on-demand filtering by benchmark ID is recommended if files are large).

### 3. User Interface Layout

**Sidebar:**
- **Select Run:** Dropdown to choose a timestamped run directory.
- **Filter Suite:** Dropdown to filter by benchmark suite (e.g., `api_understanding`, `fix_errors`).
- **Filter Status:** Checkboxes for `PASS`, `FAIL`, `CRASH`.
- **Search:** Text input to filter by benchmark name.

**Main Area - Overview:**
- Display key metrics: Total Cases, Pass Rate %, Avg Latency.
- **Results Table:** Interactive dataframe showing:
    - Status (Icon)
    - Benchmark Name
    - Suite
    - Error Type (if failed)
    - Latency

**Main Area - Detail View:**
- When a user selects a case (or clicks a "View" button in the table):
    - **Header:** Benchmark Name & Status.
    - **Tab 1: Answer Analysis**
        - Generated Code (Code block)
        - Expected/Ground Truth (Code block)
        - Diff View (Visual comparison)
    - **Tab 2: Trace Logs / Stdout**
        - Render the sequence of events from `trace_logs`.
        - **Highlight:** Explicitly render `CLI_STDOUT_FULL` events in a large, scrollable code block for easy debugging.
    - **Tab 3: Metadata**
        - Prompt used (if available in logs)
        - Token usage / Cost.

### 4. Running the App
The user will start the app using:
```bash
streamlit run tools/benchmark_viewer.py
```

## detailed log rendering logic
- Iterate through `trace_logs` list.
- Format each event type distinctly:
    - `CLI_STDOUT_FULL`: Expandable code block.
    - `CLI_STDERR`: Red text or warning box.
    - `tool_use` / `tool_result`: JSON tree or table.
    - `model_response`: Markdown rendering.
