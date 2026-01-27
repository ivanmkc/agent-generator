# Experiment Report: Statistical Discovery V3 (Semantic Data Mapping)

**Date:** 2026-01-10
**Status:** **Fail**
**Agent Variant:** `ADK_STATISTICAL_V3`
**Previous Best (Baseline):** `ADK_STATISTICAL_V2` (also failing, but V3 was an attempt to fix it)

## 1. Hypothesis & Configuration
**Hypothesis:** The agent fails to access user input because it hallucinates `context.input` or `context.request`. Adding explicit instructions to "map semantically" and check for `user_content` will fix this `AttributeError`.
**Configuration:**
*   **Base Agent:** `ADK_STATISTICAL` (SequentialAgent with ReAct solver).
*   **Modifications:** Updated `solver_agent` instructions to:
    *   Mandate `get_module_help` for complex types.
    *   Explicitly warn against guessing `.input`.
    *   Suggest looking for `user_content` or `message` in the tool output.
    *   Added `search_files` tool to find definitions if imports fail.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V3 | ADK_STATISTICAL_V2 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `AttributeError` (`.input`) | `ModuleNotFoundError` | Different failure mode |
| **Avg Tokens/Turn** | ~23k | ~23k | No significant change |

## 3. Analysis vs. Previous Best
*   **Quantitative:** No improvement in pass rate.
*   **Qualitative:**
    *   **V2 Failure:** Failed on imports (`google.adk.agents.events`). It tried to import `Event` from a non-existent module.
    *   **V3 Failure:** Failed on logic. It *found* the classes (via `get_module_help` presumably, or just guessed better imports?), but then failed to use `InvocationContext` correctly.
    *   **Regression:** V3 traded an import error for a runtime attribute error. It is "progress" in the sense that the code runs further, but it is still hallucinating the API surface.

## 4. Trace Analysis (The "Why")
*   **Successes:** The agent successfully used `get_module_help` on `InvocationContext`.
*   **Failures:**
    *   **Stubborn Hallucination:** Despite the instruction "Do NOT hallucinate... look for user_content", the agent wrote `if context.input.text == ...`.
    *   **Context Blindness:** The `get_module_help` output presumably listed `user_content`, but the agent ignored it in favor of its strong prior (training data bias) that context objects have an `.input` attribute.
    *   **Trace ID:** `benchmark_runs/2026-01-10_19-57-23` (V3 Attempt 1).

## 5. Conclusion & Next Steps
*   **Verdict:** **Iterate**. The instruction is not strong enough to override the model's training bias for `context.input`.
*   **Action Items:**
    1.  **Pivot:** We need to force the agent to *prove* it knows the field name.
    2.  **New Constraint:** "You must output the field name you selected from the `get_module_help` output in your reasoning trace *before* writing code."
    3.  **Experiment 24:** Implement `ADK_STATISTICAL_V4` with "Proof of Knowledge" prompting.
