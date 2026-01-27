# Experiment Report: Statistical Discovery V18 (Format Fix & Agent Preference)

**Date:** 2026-01-10
**Status:** **Fail** (Logic)
**Agent Variant:** `ADK_STATISTICAL_V18`
**Previous Best (Baseline):** `ADK_STATISTICAL_V14`

## 1. Hypothesis & Configuration
**Hypothesis:** Switching to Markdown/Python output format would fix parsing errors, and inheriting from `Agent` would fix constructor validation errors.
**Configuration:**
*   **Modifications:**
    *   Instructions: "Output Markdown + Python block", "Prefer inheriting from `Agent`".
    *   Validation Table retained.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V18"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V18 | ADK_STATISTICAL_V14 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `NotImplementedError` | `AssertionError` | **Regression** (Method) |
| **Avg Tokens/Turn** | ~14k | ~14k | Stable |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Stable.
*   **Qualitative:**
    *   **Parsing Success:** The runner successfully parsed the code block.
    *   **Constructor Success:** The agent successfully initialized the class without `ValidationError`.
    *   **Method Failure:** The agent failed to implement `_run_async_impl`.
    *   **Root Cause:** By focusing on `Agent` (the concrete class), the agent lost visibility into the abstract requirements defined in `BaseAgent` (the parent). It didn't realize it needed to override the core loop method.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_22-43-49`
*   **Failures:**
    *   **Information Silo:** `Agent` documentation likely doesn't repeat the abstract methods of `BaseAgent`. The agent didn't "look up" the hierarchy.

## 5. Conclusion & Next Steps
*   **Verdict:** **Hybrid Approach.**
    *   We must inherit from `Agent` to satisfy type checks.
    *   We must inspect `BaseAgent` to satisfy implementation requirements.
*   **Action Items:**
    1.  **Validation Table Update:** Add a "Methods" section to the validation table.
    2.  **Instruction:** "Check `BaseAgent` for abstract methods even if you inherit from `Agent`."
    3.  **Experiment 39:** Implement `ADK_STATISTICAL_V19`.
