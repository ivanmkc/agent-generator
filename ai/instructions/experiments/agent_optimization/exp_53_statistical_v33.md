# Experiment Report: Statistical Discovery V33 (Fast Retrieval)

**Date:** 2026-01-11
**Status:** **Verifying (Debug v4 Success)**
**Agent Variant:** `ADK_STATISTICAL_V33`
**Previous Best (Baseline):** `ADK_STATISTICAL_V29`

## 1. Hypothesis & Configuration
**Hypothesis:** The V32 architecture (Expert Delegation) is sound, but the retrieval component (V29) is too slow. V33 replaces the LLM-based `ContextExpander` with a deterministic code-based agent and refactors the Delegator for full visibility.

**Configuration:**
*   **Context Expander:** `ContextExpanderCodeBased` (Code-based loop).
    *   Speedup: ~120s down to **< 1s**.
*   **Delegator:** `RoutingDelegatorAgent` (Custom Agent).
    *   YIELDS all events from sub-agents (Visibility fix).
*   **Finalizer:** Schema-driven task inference.

## 2. Iteration Log

### 2.1 Debug Run 1-3
*   Fixed `await` bug (sync function).
*   Fixed Regex bug (matched tuple string instead of markdown list).
*   Optimized setup with local cache of `adk-python`.

### 2.2 Debug Run 4 (Success)
*   **Result:** Passed MCQ task in **10.2s** (Flash) and **32.8s** (Pro).
*   **Visibility:** Confirmed all authors (`router`, `seed_selector`, `qa_solver`, etc.) appear in trace.
*   **Token Efficiency:** Turn cost ~5k tokens.

## 3. Results Comparison (Debug MCQ)
| Metric | ADK_STATISTICAL_V33 | ADK_STATISTICAL_V32 |
| :--- | :--- | :--- |
| **Status** | **Pass** | **Fail** (Validation) |
| **Latency** | **10.2s** | ~120s |
| **Visibility**| Full (All authors) | Partial (Tools only) |

## 4. Conclusion & Next Steps
*   **Status:** V33 is Pareto-Optimal (Fast + Accurate).
*   **Next Step:** Running full `debug_suite` to verify Coding Specialist.
