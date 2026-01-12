# Experiment Report: Statistical Discovery V25 (Index Retrieval)

**Date:** 2026-01-10
**Status:** **Fail** (Index Ambiguity)
**Agent Variant:** `ADK_STATISTICAL_V25`
**Previous Best (Baseline):** `ADK_STATISTICAL_V24`

## 1. Hypothesis & Configuration
**Hypothesis:** Replacing dynamic retrieval with index-based retrieval would provide stable context, and a "Signature Guard" would prevent the validation error from V24.
**Configuration:**
*   **Modifications:**
    *   Retrieval: `_create_index_retrieval_agents_v25`.
    *   Instructions: "Signature MUST be `-> BaseAgent`".
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V25"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V25 | ADK_STATISTICAL_V24 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `ValidationError` | `ModelAnswerDidNotMatchTemplate` | **Regression** (Init) |
| **Avg Tokens/Turn** | ~14k | ~14k | Stable |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Stable.
*   **Qualitative:**
    *   **Index Failure:** The index lists `BaseAgent` and `LlmAgent` but not `Agent` explicitly (as `Agent` is an alias in `llm_agent`).
    *   **Context Gap:** The retrieval agent fetched `BaseAgent` but not `LlmAgent`/`Agent` (or didn't link them).
    *   **Constructor Failure:** The solver inherited from `BaseAgent` (safe choice given context) but used `Agent`'s constructor arguments (`model`, `instruction`) because of the "Prefer Agent" prompt. This caused a Pydantic error because `BaseAgent` doesn't take those args.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_23-39-56`
*   **Failures:**
    *   **Identity Crisis:** `Agent` IS `LlmAgent`. The agent didn't know this from the index context alone.

## 5. Conclusion & Next Steps
*   **Verdict:** **Target LlmAgent.**
    *   Since `Agent` is `LlmAgent`, we must fetch `google.adk.agents.llm_agent`.
    *   We must inherit from `Agent` (aka `LlmAgent`) to support the `model` arg provided in `create_agent`.
*   **Action Items:**
    1.  **Instruction Update:** Tell module selector to target `google.adk.agents.llm_agent`.
    2.  **Solver Update:** "Inherit `Agent`. Pass `model`."
    3.  **Experiment 46:** Implement `ADK_STATISTICAL_V26`.
