# Experiment Report: Statistical Discovery V26 (Targeted Retrieval)

**Date:** 2026-01-10
**Status:** **Fail** (Constructor Mystery)
**Agent Variant:** `ADK_STATISTICAL_V26`
**Previous Best (Baseline):** `ADK_STATISTICAL_V21`

## 1. Hypothesis & Configuration
**Hypothesis:** Using targeted index retrieval to find `google.adk.agents.llm_agent` would confirm `Agent` identity and allow successful inheritance/initialization.
**Configuration:**
*   **Modifications:**
    *   Retrieval: Target `llm_agent`.
    *   Instructions: "Inherit `Agent`, pass `model`".
    *   Refactored setup hook.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V26"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V26 | ADK_STATISTICAL_V25 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `ValidationError` | `ValidationError` | Stable Failure |
| **Avg Tokens/Turn** | ~14k | ~14k | Stable |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Stable.
*   **Qualitative:**
    *   **Persistent Failure:** Despite confirming `Agent is LlmAgent` in shell checks, the generated code consistently fails Pydantic validation when passing `model` to `Agent`.
    *   **The Paradox:** The runtime environment behaves as if `Agent` does *not* accept `model`, contradicting the static code analysis.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_23-44-56`
*   **Failures:**
    *   `ValidationError` implies `extra='forbid'` triggered on `model`.
    *   This forces us to abandon the `Agent` inheritance path if we can't reliably pass arguments.

## 5. Conclusion & Next Steps
*   **Verdict:** **Back to Base.**
    *   Inherit from `BaseAgent`.
    *   Do NOT pass `model`/`instruction` to `super`.
    *   Manually handle these args.
*   **Action Items:**
    1.  **Instruction:** "Inherit `BaseAgent`. Call `super().__init__(name=name)` ONLY."
    2.  **Experiment 47:** Implement `ADK_STATISTICAL_V27`.
