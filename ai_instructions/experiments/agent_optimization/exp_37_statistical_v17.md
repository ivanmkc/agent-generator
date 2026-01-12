# Experiment Report: Statistical Discovery V17 (Validation Table)

**Date:** 2026-01-10
**Status:** **Fail** (Parsing & Logic)
**Agent Variant:** `ADK_STATISTICAL_V17`
**Previous Best (Baseline):** `ADK_STATISTICAL_V14`

## 1. Hypothesis & Configuration
**Hypothesis:** Forcing the agent to output a "Validation Table" before coding would compel it to verify constructor arguments against the context, preventing `ValidationError`.
**Configuration:**
*   **Modifications:**
    *   Instructions: "VALIDATION TABLE (MANDATORY)".
    *   Retained V16 architecture.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V17"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V17 | ADK_STATISTICAL_V16 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `ModelAnswerDidNotMatchTemplate` | `ValidationError` | **Regression** (Tooling) |
| **Avg Tokens/Turn** | ~14k | ~14k | Stable |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Stable.
*   **Qualitative:**
    *   **Parsing Failure:** The agent embedded the Validation Table inside the `rationale` string of the JSON output, or formatted it in a way that broke `CodeBasedRunner`'s regex/JSON parsing. This resulted in `"# Error: Invalid JSON block found."` being executed.
    *   **Logic Failure:** Inspection of the generated code (which failed to run) shows the agent *hallucinated* in the validation table. It claimed `instruction` and `model` were valid fields for `BaseAgent` because it conflated it with `Agent`.
    *   **Method Hallucination:** It implemented `__call__` instead of `_run_async_impl`.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_22-37-11`
*   **Failures:**
    *   **Self-Delusion:** The validation table didn't work because the agent verified its own hallucinations ("Agent requires instruction, so BaseAgent must too").
    *   **Format Fragility:** Asking for complex reasoning inside a JSON string is error-prone.

## 5. Conclusion & Next Steps
*   **Verdict:** **Simplify & Redirect.**
    *   JSON output for code is too brittle. Switch to Markdown + Python block.
    *   `BaseAgent` is too opaque. Switch back to preferring `Agent`, which actually *does* support the fields the agent wants to use.
*   **Action Items:**
    1.  **Format:** Output text reasoning -> Markdown Validation Table -> Python Code Block.
    2.  **Topology:** Revert to preferring `google.adk.agents.Agent`.
    3.  **Experiment 38:** Implement `ADK_STATISTICAL_V18`.
