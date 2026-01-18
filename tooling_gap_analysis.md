# Analysis Tooling Review: Gap Analysis & Unification Strategy

## 1. Why Existing Tools Were Insufficient
I resorted to writing ad-hoc scripts (`debug_specific_run.py`, `extract_case_details.py`) because the existing suite in `tools/analysis/` is optimized for **Aggregate Trending** and **Database Reporting**, not **Real-Time Forensic Debugging**.

### A. Latency & Dependencies
*   **Existing (`analyze_tool_failures.py`):** Requires running an ingestion pipeline (`analyze_root_causes.py`) to populate a SQLite DB. This is too heavy for checking a run that just finished.
*   **Ad-Hoc:** Reads `results.json` directly. Instant feedback.

### B. Targeting
*   **Existing (`analyze_results_json.py`):** Hardcodes the target benchmark name (`"01: A minimal LlmAgent."`). To use it, I must edit the source code for every new case I want to inspect.
*   **Ad-Hoc:** I hardcoded *my* specific targets (`api_understanding:...`) in the script.
*   **Gap:** Lack of CLI arguments for dynamic filtering.

### C. Depth of Insight
*   **Existing:** Categorizes errors into broad buckets ("Hallucination", "Timeout").
*   **Ad-Hoc:** Extracted the **Router's internal monologue**. The generic tools don't know about the specific "Router -> Coding Expert" architecture of V47, so they treat all logs as flat tool calls. I needed to see the *hierarchical* decision path.

## 2. Comparison Matrix

| Feature | `tools/analysis/analyze_results_json.py` | `debug_specific_run.py` (My Script) |
| :--- | :--- | :--- |
| **Input** | `results.json` | `results.json` |
| **Selection** | Hardcoded String Match | List of IDs / Regex |
| **Output** | Tool Call List (Flat) | Semantic Trace (Router -> Expert -> Output) |
| **Use Case** | Tool Usage Audit | Architectural Debugging |

## 3. Unification Recommendation: `inspect_run.py`

We should replace the rigid `analyze_results_json.py` and my ad-hoc scripts with a single, robust CLI tool: **`tools/analysis/inspect_run.py`**.

### Proposed Features:
1.  **Dynamic Filtering:**
    ```bash
    python tools/analysis/inspect_run.py --run latest --filter "callback_method"
    ```
2.  **Architectural Awareness (The "Trace Projector"):**
    Instead of dumping raw tool calls, it should recognize agent patterns:
    *   *If Router detected:* Print "Routing: [Decision]".
    *   *If Retrieval Loop:* Summarize "Browsed 5 pages, inspected [X, Y]".
    *   *If Error:* Print the exact Validation Error diff.
3.  **Direct Mode:**
    Bypasses the SQLite DB. Reads `results.json` or `trace.jsonl` directly for immediate feedback.

### Immediate Action
I will refactor `tools/analysis/analyze_results_json.py` to accept command-line arguments for the run ID and benchmark filter, effectively converting it into the `inspect_run.py` prototype. This solves the immediate friction.
