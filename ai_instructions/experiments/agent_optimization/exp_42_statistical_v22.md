# Experiment Report: Statistical Discovery V22 (Input Access)

**Date:** 2026-01-10
**Status:** **Fail** (Constructor Regression)
**Agent Variant:** `ADK_STATISTICAL_V22`
**Previous Best (Baseline):** `ADK_STATISTICAL_V21`

## 1. Hypothesis & Configuration
**Hypothesis:** Fixing the `ctx.input` access path would solve the `AttributeError` from V21.
**Configuration:**
*   **Modifications:**
    *   Instructions: "Access `ctx.user_content`".
    *   Retained V21 architecture.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V22"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V22 | ADK_STATISTICAL_V21 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `ValidationError` | `AttributeError` | **Regression** |
| **Avg Tokens/Turn** | ~14k | ~14k | Stable |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Stable.
*   **Qualitative:**
    *   **Regression:** The agent switched back to inheriting from `BaseAgent` (instead of `Agent`) but still passed `instruction` and `model` to the constructor, causing Pydantic validation errors.
    *   **Reasoning:** It prioritized the function return type hint (`-> BaseAgent`) over the "Prefer Agent" instruction.
    *   **Missed Opportunity:** V21 successfully used `Agent` and passed init. V22 regressed on this while trying to fix the input access.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_22-59-57`
*   **Failures:**
    *   **Inconsistency:** The prompt rules were slightly conflicting ("Prefer Agent" vs "Strict Source of Truth" + Return Type Hint). The agent resolved this conservatively by choosing `BaseAgent` but liberally by passing `Agent` args.

## 5. Conclusion & Next Steps
*   **Verdict:** **Combine V21 & V22.**
    *   Use V21's inheritance (`Agent`).
    *   Use V22's input access (`ctx.user_content`).
*   **Action Items:**
    1.  **Instruction:** "Inherit from `Agent` (which satisfies `BaseAgent` return type)."
    2.  **Experiment 43:** Implement `ADK_STATISTICAL_V23`.
