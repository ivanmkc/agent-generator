# Experiment Report: Statistical Discovery V29 (Association-Aware Retrieval)

**Date:** 2026-01-11
**Status:** **Pending**
**Agent Variant:** `ADK_STATISTICAL_V29`
**Previous Best (Baseline):** `ADK_STATISTICAL_V28`

## 1. Hypothesis & Configuration
**Hypothesis:** Replacing flat index retrieval with a **Agentic-inspired Association-Aware** strategy will improve context quality. By using real-world co-occurrence probabilities ($P(B|A)$), the agent can automatically discover related modules (e.g., discovering that `google.adk.events` is frequently used with `google.adk.agents.llm_agent`) even if they aren't explicitly mentioned in the request.

**Configuration:**
*   **Base:** V28 (Error Loop).
*   **New Tool:** `get_api_associations(entity_name)` - Returns statistically relevant related modules.
*   **New Pipeline:**
    1.  **Seed Selector:** Picks core modules from `adk_index.yaml`.
    2.  **Context Expander:** Calls `get_api_associations` for each seed to pull in dependencies.
    3.  **Docstring Fetcher:** Gathers API truth for the expanded set.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "fix_errors" --generator-filter "ADK_STATISTICAL_V29"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V29 | ADK_STATISTICAL_V28 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Fix Errors)** | TBD | 58.3% | TBD |
| **Avg Tokens/Turn** | TBD | ~14k | TBD |

## 3. Analysis
*   **Expected Behavior:** The agent should provide more complete implementations by "knowing" about necessary helper classes (like `Event` or `InvocationContext`) without needing them in the user prompt.

## 4. Conclusion & Next Steps
*   Run the benchmark and verify if association-aware discovery reduces `ImportError` or `AttributeError` caused by missing context.
