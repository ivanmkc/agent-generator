# Experiment Report: Statistical Discovery V10 (Robust Retrieval)

**Date:** 2026-01-10
**Status:** **Fail** (But Significant Progress)
**Agent Variant:** `ADK_STATISTICAL_V10`
**Previous Best (Baseline):** `ADK_STATISTICAL_V9`

## 1. Hypothesis & Configuration
**Hypothesis:** A robust 3-stage pipeline with a deterministic code-based fetcher will eliminate flaky tool-calling and provide the solver with perfect context, resolving the `NotImplementedError` and `ImportError` issues.
**Configuration:**
*   **Modifications:**
    *   `RobustKnowledgeAgent`: Handles both strings and objects in session state.
    *   `module_proposer`: Explicitly instructed to find types and parent classes.
    *   `solver_agent`: Prompted with "AsyncGenerator Enforcement" and "Pydantic Kwarg Rule".
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V10 | ADK_STATISTICAL_V9 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `ValidationError` (`instruction`) | `NotImplementedError` | Significant Logic Improvement |
| **Avg Tokens/Turn** | ~14k | ~14k | Stable |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Token usage remains highly efficient.
*   **Qualitative:** 
    *   **Major Success:** The agent successfully implemented `_run_async_impl` using `yield` and `AsyncGenerator`. This is a huge win for signature compliance.
    *   **Major Success:** The agent correctly used keyword arguments (`name=name`) for the constructor.
    *   **Failure:** The agent hallucinated that `BaseAgent` has an `instruction` field. It mixed the schema of `BaseAgent` with its knowledge of `LlmAgent`.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_21-04-26`
*   **Failures:**
    *   **Schema Contamination:** The agent saw the correct fields for `BaseAgent` in the `API TRUTH CONTEXT`, but its internal "prior" for ADK agents having instructions was too strong. It added `instruction=agent_instruction` to the `super().__init__` call, triggering a Pydantic `extra_forbidden` error.

## 5. Conclusion & Next Steps
*   **Verdict:** **Iterate**. We are now extremely close. The agent has the right tools and topology; it just needs a "Schema Guard" to stop it from adding unverified fields.
*   **Action Items:**
    1.  **Pivot:** Add a "Schema Guard" instruction: "ONLY use fields explicitly listed in the provided API Reference. If a field like `instruction` is not listed for the class you are using, do NOT pass it."
    2.  **Experiment 31:** Implement `ADK_STATISTICAL_V11` with strict schema adherence.
