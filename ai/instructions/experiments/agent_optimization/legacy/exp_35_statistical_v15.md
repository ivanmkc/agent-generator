# Experiment Report: Statistical Discovery V15 (Class Preference)

**Date:** 2026-01-10
**Status:** **Fail**
**Agent Variant:** `ADK_STATISTICAL_V15`
**Previous Best (Baseline):** `ADK_STATISTICAL_V14`

## 1. Hypothesis & Configuration
**Hypothesis:** Preferring `google.adk.agents.Agent` over `BaseAgent` would align with the test's `isinstance` expectations and resolve the `AssertionError` seen in V14.
**Configuration:**
*   **Modifications:**
    *   Instructions: "Prefer inheriting from `Agent`...".
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V15"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V15 | ADK_STATISTICAL_V14 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `NotImplementedError` | `AssertionError` | **Regression** |
| **Avg Tokens/Turn** | ~12k | ~14k | - |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Stable token usage.
*   **Qualitative:**
    *   **Regression:** The agent failed to implement the required abstract method `_run_async_impl`.
    *   **Hallucination:** Instead, it implemented `_handle_message`, likely a hallucination from a different agent framework or an older ADK version it "remembered" or inferred from `Agent` documentation (which wasn't fully visible).
    *   **Root Cause:** Switching to `Agent` obscured the clear contract provided by `BaseAgent` (which V14 successfully identified as requiring `_run_async_impl`).

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_22-28-07`
*   **Failures:**
    *   **Contract Violation:** `LogicAgent` inherited from `BaseAgent` (ignoring the preference instruction partially) but failed to implement the abstract method, leading to `NotImplementedError` at runtime.

## 5. Conclusion & Next Steps
*   **Verdict:** **Revert to V14.** The V14 architecture (BaseAgent + Type Conservatism) was correct. The `AssertionError` is an import path issue.
*   **Action Items:**
    1.  **Pivot:** Revert to V14 instructions.
    2.  **Fix Import:** Explicitly instruct the agent to import `BaseAgent` from its *canonical definition module* (`google.adk.agents.base_agent`) to attempt to bypass the test runner's potential namespace reloading issues.
    3.  **Experiment 36:** Implement `ADK_STATISTICAL_V16` with "Canonical Import Strategy".
