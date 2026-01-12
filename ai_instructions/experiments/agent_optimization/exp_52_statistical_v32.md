# Experiment Report: Statistical Discovery V32 (Strict Delegation)

**Date:** 2026-01-11
**Status:** **Debugging**
**Agent Variant:** `ADK_STATISTICAL_V32`
**Previous Best (Baseline):** `ADK_STATISTICAL_V29`

## 1. Hypothesis & Configuration
**Hypothesis:** By creating two distinct, specialized `AgentTools`—one for Coding (V29) and one for Knowledge (Retrieval + QA Solver)—we can allow a simple `Delegator` to route requests effectively. This avoids the "Swiss Army Knife" problem where a single agent tries to do everything and gets confused about output formats.

**Configuration:**
*   **Coding Tool (`prismatic_solver_v29`):** The proven V29 pipeline.
*   **Knowledge Tool (`knowledge_specialist`):** Retrieval Agents + `qa_solver` (optimized for JSON QA).
*   **Delegator:** Routes based on intent.

## 2. Iteration Log

### 2.1 Initial Run (Fail)
*   **Result:** 0% Pass Rate.
*   **Symptoms:**
    *   `Validation Error`: The finalizer failed to detect the `MultipleChoiceAnswerOutput` correctly because the sanitized user request did not contain the class name string.
    *   `Empty Result`: The `TeardownAgent` overwrote the final response because state was not propagated.
    *   `Latency`: Extreme latency (>2 mins per task) in the `knowledge_specialist`.

### 2.2 Fix Applied (Schema & State)
*   **Action:** Patched `ExpertResponseFinalizer`.
    *   Infer output type from JSON structure (`answer` vs `code`).
    *   Explicitly save result to `ctx.session.state["final_response"]`.
*   **Status:** Running verification.

## 3. Results Comparison
| Metric | ADK_STATISTICAL_V32 | ADK_STATISTICAL_V29 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | TBD | 66.7% | TBD |
| **Coding Task** | TBD | Pass | TBD |
| **QA Tasks** | TBD | Fail | TBD |

## 4. Analysis
*   **Goal:** 100% Pass on Debug Suite (1 Coding, 2 QA).

## 5. Conclusion & Next Steps
*   Run the benchmark to verify the fix.
*   Investigate V29 retrieval latency.