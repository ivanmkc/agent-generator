# Experiment Report: Statistical Discovery V21 (Super Call)

**Date:** 2026-01-10
**Status:** **Fail** (Input Access)
**Agent Variant:** `ADK_STATISTICAL_V21`
**Previous Best (Baseline):** `ADK_STATISTICAL_V14`

## 1. Hypothesis & Configuration
**Hypothesis:** Mandating `super().__init__` call would fix the Pydantic initialization error seen in V20.
**Configuration:**
*   **Modifications:**
    *   Instructions: "MUST call `super().__init__`".
    *   Retained V20 architecture.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V21"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V21 | ADK_STATISTICAL_V20 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `AttributeError` (ctx.input) | `AttributeError` (name) | **Progress** |
| **Avg Tokens/Turn** | ~14k | ~14k | Stable |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Stable.
*   **Qualitative:**
    *   **Constructor Success:** The agent called `super().__init__`, resolving the `name` attribute error.
    *   **Logic Success:** Correctly implemented `AsyncGenerator` logic.
    *   **New Failure:** `AttributeError: 'InvocationContext' object has no attribute 'input'`.
    *   **Reasoning:** The agent assumed `ctx.input.text` was the way to access user input. This was a guess because context was missing or unclear.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_22-56-19`
*   **Failures:**
    *   **Missing Knowledge:** `InvocationContext` uses `user_content` (of type `google.genai.types.Content`), not `input`.

## 5. Conclusion & Next Steps
*   **Verdict:** **Fix Input Access.**
    *   The structure is solid.
    *   We need to tell the agent the correct path to the user message: `ctx.user_content.parts[0].text`.
*   **Action Items:**
    1.  **Instruction:** Explicitly describe `InvocationContext.user_content` structure.
    2.  **Experiment 42:** Implement `ADK_STATISTICAL_V22`.
