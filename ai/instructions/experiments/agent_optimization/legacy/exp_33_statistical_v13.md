# Experiment Report: Statistical Discovery V13 (Smart Retrieval)

**Date:** 2026-01-10
**Status:** **Fail** (Near Success)
**Agent Variant:** `ADK_STATISTICAL_V13`
**Previous Best (Baseline):** `ADK_STATISTICAL_V11`

## 1. Hypothesis & Configuration
**Hypothesis:** Improving the fetcher to handle class-like paths and parent modules will resolve the retrieval blackout, allowing the solver to see the correct API.
**Configuration:**
*   **Modifications:**
    *   `SmartKnowledgeAgent`: Splits class paths to find parent modules.
    *   Instructions: "No Hallucinations", "Missing Classes", "Keyword Only".
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V13"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V13 | ADK_STATISTICAL_V12 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `ImportError` (`LlmResponse`) | `ValidationError` | Regression to import issues |
| **Avg Tokens/Turn** | ~2.7k | ~14k | **-11k (Efficiency Win)** |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Extremely efficient execution (under 3k tokens for implementation).
*   **Qualitative:**
    *   **Retrieval Success:** The fetcher successfully found `google.adk`, `google.adk.agents`.
    *   **Logic Success:** The agent correctly defined `LogicAgent` locally, used `AsyncGenerator`, and used keyword args.
    *   **Failure:** The agent hallucinated `from google.adk import LlmResponse`. This class does not exist (or wasn't in the context). The agent assumed it existed based on the `LlmAgent` name pattern.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_21-51-40`
*   **Failures:**
    *   **Hallucination:** Despite strict "No Hallucinations" rules, the model invented a return type `LlmResponse` because it felt `LogicAgent` needed to return something "official".
    *   **Context Gap:** The context likely didn't show what `BaseAgent` methods should return (generic `Event` or `str`), so the agent guessed.

## 5. Conclusion & Next Steps
*   **Verdict:** **Fix the Return Type.** We are one import away from success.
*   **Action Items:**
    1.  **Pivot:** Explicitly instruct the agent to use standard Python types or `Event` (if verified) for return values.
    2.  **Experiment 34:** Implement `ADK_STATISTICAL_V14` with "Type Conservatism".
