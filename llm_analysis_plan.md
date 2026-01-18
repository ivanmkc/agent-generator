# Plan: LLM-Based Root Cause Analysis

## Objective
Analyze detailed benchmark trace logs using a Gemini model to determine the *true* root cause of failures, going beyond simple regex.

## 1. Prerequisites & Setup
*   **Model:** Use `gemini-2.0-flash-exp` (proxy for "Gemini 3.0" requested by user, or latest available) for speed/cost balance, or `gemini-1.5-pro` for reasoning depth. I will use `gemini-2.0-flash-exp` as the default analyzer.
*   **Auth:** Use `benchmarks.api_key_manager.API_KEY_MANAGER` to get keys.
*   **Client:** Use `google.genai` library.

## 2. Database Updates
*   **Table:** `failures` (Update schema)
    *   Add `llm_analysis` (TEXT)
    *   Add `llm_root_cause` (TEXT)
    *   Add `trace_log_path` (TEXT) - to help caching/re-runs without re-scanning files.

## 3. Script Logic: `tools/analysis/llm_root_cause_analysis.py`

### A. Data Gathering (Producer)
1.  Read `benchmarks/analysis_cache.db` to get the list of failed runs and their `run_id`.
2.  Locate the corresponding `trace.jsonl` file.
3.  Extract the **full trace logs** for the failed attempt.
    *   *Constraint:* Limit trace size to ~50k tokens (truncate middle if necessary) to stay within reasonable limits, though Gemini 2.0 has 1M context. I'll send full logs unless > 500kb text.

### B. Analysis (Consumer/Worker)
1.  **Prompt:**
    *   Input: `Benchmark Name`, `Error Message`, `Trace Logs (JSONL string)`.
    *   Task: Analyze the agent's behavior.
    *   Questions:
        *   Did it use tools? Which ones?
        *   Did it receive useful output?
        *   Did it hallucinate imports/attributes?
        *   Did it fail Pydantic validation (formatting)?
    *   Output Schema (JSON):
        *   `root_cause_category`: Enum [Context Starvation, Hallucination, Tool Misuse, Schema Violation, Logic Error, Infrastructure]
        *   `explanation`: Concise reason.
        *   `expected_behavior`: What it should have done.
        *   `actual_behavior`: What it did.

2.  **Concurrency:**
    *   Use `asyncio.Semaphore` (limit 5-10 concurrent requests).
    *   Use `ApiKeyManager` to rotate keys.

3.  **Persistence:**
    *   Update the SQLite row with the LLM's JSON output.

### C. Reporting
*   Update `write_notebook.py` to pull the `llm_root_cause` column instead of the regex one.

## 4. Execution Steps
1.  **Modify DB:** Add columns to `analysis_cache.db`.
2.  **Write Script:** `tools/analysis/llm_root_cause_analysis.py`.
3.  **Run Script:** Execute analysis.
4.  **Update Notebook:** Visualize LLM-derived insights.
