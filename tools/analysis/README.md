# Benchmark Analysis Toolkit

This directory contains a suite of tools for analyzing agent performance, debugging failures, and managing benchmark data. The tools operate in two modes: **Database-Backed** (for aggregate analysis) and **Standalone** (for single-trace inspection).

## 1. Automated Root Cause Analysis (The DB Pipeline)

This pipeline automatically ingests benchmark traces into a SQLite database (`benchmarks/analysis_cache.db`), classifies errors using Regex, and optionally uses an LLM to perform forensic analysis on failures.

### Step 1: Ingest & Classify
Scans the `benchmark_runs/` directory for new `trace.jsonl` files (last 2 days by default) and populates the database. It uses Regex to categorize errors (e.g., "ImportError", "Schema Violation").

```bash
python tools/analysis/analyze_root_causes.py
```
*   **Arguments:** None (Configured via `RUNS_DIR` and `DB_PATH` in script).
*   **Output:** Creates/Updates `benchmarks/analysis_cache.db`.

### Step 2: LLM Forensic Audit
Queries the database for unanalyzed failures and uses Gemini to analyze the trace logs. It determines *why* the agent failed (e.g., "Hallucinated API", "Ignored Tool Output").

```bash
python tools/analysis/llm_root_cause_analysis.py
```
*   **Prerequisites:** Requires valid API keys in `settings.json` or env vars.
*   **Output:** Updates the `llm_analysis` and `llm_root_cause` columns in the database.

### Step 3: Generate Reports
Once data is in the DB, use these scripts to generate insights.

**A. Failure Mode Statistics**
Prints aggregate stats on which tools are failing and why (e.g., "How many failures were due to empty search results?").
```bash
python tools/analysis/analyze_tool_failures.py
```

**B. Deep Dive on Tool Chains**
Extracts the exact sequence of tool calls (e.g., `get_module_help` -> `search_files`) for failed runs to see where the agent went off track.
```bash
python tools/analysis/deep_dive_tool_params.py
```

---

## 2. Standalone Trace Inspection

These tools work directly on `trace.jsonl` files without needing the database.

### `analyze_benchmark_chunks.py`
Parses a raw trace file and outputs a clean Markdown table of every benchmark case, its pass/fail status, token usage, and duration.

**Usage:**
```bash
python tools/analysis/analyze_benchmark_chunks.py <path_to_trace.jsonl>
```

**Example:**
```bash
python tools/analysis/analyze_benchmark_chunks.py benchmark_runs/2026-01-13_04-07-18/trace.jsonl
```

**Output:**
```text
Benchmark Case                                     | Generator                                | Status     | Tokens     | Time (s)  
========================================================================================================================
01: A minimal LlmAgent...                          | ADK_STATISTICAL_V41                      | PASS       | 4032       | 12.50     
02: A tool-using agent...                          | ADK_STATISTICAL_V41                      | FAIL       | 15201      | 45.20     
```

### `analyze_traces.py`
A lightweight script to filter traces for specific events (like specific tool calls).
*   **Usage:** Requires editing the `log_file` variable in the `__main__` block.
*   **Goal:** Quickly checking "Which benchmarks actually called `run_adk_agent`?"

---

## 3. Comparison & Advanced Tools

These scripts are often used as templates or require specific configuration for A/B testing.

### `compare_adk_variants.py`
Runs two different agent configurations side-by-side against the same benchmark suite.
*   **Usage:** Edit the `candidate_1` and `candidate_2` definitions in the script, then run.
*   **Output:** Generates a combined trace log in `tmp/compare_logs/`.

### `compare_tool_usage.py`
Analyzes two trace files and compares the "Token Efficiency" of their tool usage (i.e., how verbose were the tool outputs vs. how useful they were).
*   **Usage:** Edit the file paths in the `__main__` block:
    ```python
    analyze_trace("path/to/run_A/trace.jsonl", "Variant A")
    analyze_trace("path/to/run_B/trace.jsonl", "Variant B")
    ```

---

## Database Schema (`benchmarks/analysis_cache.db`)

If you want to write custom SQL queries, the schema is:

*   **`failures` Table:**
    *   `run_id`: Timestamp string of the run.
    *   `benchmark_name`: Name of the test case.
    *   `error_type`: JSON list of regex-detected tags.
    *   `llm_root_cause`: The LLM's final verdict (e.g., "Reasoning: Ignored Context").
    *   `llm_analysis`: Full JSON output from the forensic agent.
    *   `explanation`: Brief error snippet.