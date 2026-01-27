# Experiment Report: Statistical Discovery V7 (Pydantic Kwarg Enforcement)

**Date:** 2026-01-10
**Status:** **Fail**
**Agent Variant:** `ADK_STATISTICAL_V7`
**Previous Best (Baseline):** `ADK_STATISTICAL_V6`

## 1. Hypothesis & Configuration
**Hypothesis:** Explicitly mandating Keyword Arguments for Pydantic models (subclasses of `BaseAgent`) will resolve the `TypeError` where positional arguments were passed to `super().__init__()`.
**Configuration:**
*   **Modifications:**
    *   Added "PYDANTIC KWARG RULE" to instructions.
    *   Mandated `name=name` syntax for all initializations.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V7 | ADK_STATISTICAL_V6 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `ImportError` (`AgentOutput`) | `TypeError` | Reverted to import issues |
| **Avg Tokens/Turn** | ~16k | ~11k | +5k (Slightly wordier) |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Token usage increased slightly, but still well under the 15k threshold for the implementation turn.
*   **Qualitative:**
    *   **Success:** The `TypeError` was resolved. The agent used `super().__init__(name=name)`.
    *   **Failure:** The agent hallucinated a class `AgentOutput` in `google.adk.agents`. 
    *   **Root Cause:** The agent is still guessing module contents. It sees `Event` and `InvocationContext` and assumes other similar-sounding classes exist in the same namespace.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_20-44-02` (V7 Attempt 2).
*   **Failures:**
    *   **Import Guessing:** The agent wrote `from google.adk.agents import BaseAgent, AgentOutput`.
    *   **Tool Bypass:** It did NOT call `get_module_help` or `search_files` specifically for `AgentOutput` before importing it. It relied on its training data bias for "Agent" library patterns.

## 5. Conclusion & Next Steps
*   **Verdict:** **Iterate**. We have solved the constructor logic but imports remain the final hurdle.
*   **Action Items:**
    1.  **Pivot:** We must implement a "Strict Import Verification" step.
    2.  **Constraint:** "You are FORBIDDEN from importing any class unless you have verified its module path using `search_files(class_name)`."
    3.  **Experiment 28:** Implement `ADK_STATISTICAL_V8` with "Import Guard" instructions.
