# Experiment Report: Statistical Discovery V4 (Proof of Knowledge)

**Date:** 2026-01-10
**Status:** **Fail**
**Agent Variant:** `ADK_STATISTICAL_V4`
**Previous Best (Baseline):** `ADK_STATISTICAL_V3` (Fail - AttributeError)

## 1. Hypothesis & Configuration
**Hypothesis:** Forcing the agent to explicitly "Prove Knowledge" (quote discovered fields) before writing code will prevent it from hallucinating non-existent attributes like `context.input`.
**Configuration:**
*   **Base Agent:** `ADK_STATISTICAL`
*   **Modifications:**
    *   Added "PROOF OF KNOWLEDGE" section to instructions.
    *   Explicitly banned `context.input` / `context.request` unless proven.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V4"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V4 | ADK_STATISTICAL_V3 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `Tool 'read_file' not found` | `AttributeError` | Regression (Tool Starvation) |
| **Avg Tokens/Turn** | N/A (Failed early) | ~23k | - |

## 3. Analysis vs. Previous Best
*   **Quantitative:** No improvement.
*   **Qualitative:** The agent attempted to verify its knowledge (likely by reading a file definition) but was blocked because the `read_file` tool was not provided in this restricted debug configuration.
*   **Regression:** The strict protocol worked *too* well—it drove the agent to seek ground truth via file reading, which was impossible, leading to a crash.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_20-20-06`
*   **Failures:**
    *   **Tool Starvation:** The agent tried to call `read_file`. I checked `experiment_24.py` and indeed, `read_tool` is missing from the `tools=[...]` list for `solver_agent`.
    *   **Reasoning:** The agent likely found a file via `search_files` and wanted to inspect it to satisfy the "Proof of Knowledge" requirement, but `get_module_help` might have been insufficient or it preferred raw source.

## 5. Conclusion & Next Steps
*   **Verdict:** **Fix & Retry**. The hypothesis wasn't fully tested because the agent lacked the tools to comply with the rigorous verification protocol.
*   **Action Items:**
    1.  **Experiment 25:** Clone V4 but add `read_file` to the `solver_agent`'s toolset.
    2.  **Refine Instructions:** Explicitly mention `read_file` as a valid way to obtain "Proof of Knowledge".
