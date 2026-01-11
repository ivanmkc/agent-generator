# Experiment Report: Statistical Discovery V30 (Task-Based Delegation)

**Date:** 2026-01-11
**Status:** **Pending**
**Agent Variant:** `ADK_STATISTICAL_V30`
**Previous Best (Baseline):** `ADK_STATISTICAL_V29`

## 1. Hypothesis & Configuration
**Hypothesis:** The V29 agent is highly optimized for writing code but lacks the flexibility to handle "knowledge" tasks like Multiple Choice or API Understanding questions, often hallucinating code blocks instead of JSON answers. By introducing a **Delegator Agent**, we can route requests to specialized sub-agents: a `CodeWriter` (for implementation) and a `KnowledgeExpert` (for QA).

**Configuration:**
*   **Base:** V29 (Prismatic Retrieval).
*   **Modifications:**
    *   **DelegatorAgent:** Analyzes the request and calls either `run_code_writer` or `run_knowledge_expert`.
    *   **CodeWriter:** Encapsulates the V29 Loop (Solver -> Runner -> Analyst).
    *   **KnowledgeExpert:** A new single-turn agent optimized for accurate QA using the same retrieved context.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug_suite" --generator-filter "ADK_STATISTICAL_V30"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V30 | ADK_STATISTICAL_V29 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug Suite)** | TBD | N/A | TBD |
| **Fix Error Rate** | TBD | 75.0% | TBD |

## 3. Analysis
*   **Expected Behavior:**
    *   Coding tasks -> Route to Loop -> Pass.
    *   QA tasks -> Route to Expert -> Pass.

## 4. Conclusion & Next Steps
*   Run the mixed `debug_suite`.
