# Experiment Report: Statistical Discovery V28 (Error Recovery Loop)

**Date:** 2026-01-11
**Status:** **Pending**
**Agent Variant:** `ADK_STATISTICAL_V28`
**Previous Best (Baseline):** `ADK_STATISTICAL_V27`

## 1. Hypothesis & Configuration
**Hypothesis:** The V27 architecture (Pass Rate 50%) fails because it lacks an error recovery mechanism. If the generated code has syntax errors or runtime issues (e.g., `ValidationError`), the pipeline terminates without attempting a fix. Wrapping the `Solver` and `Runner` in a `LoopAgent` with a `RunAnalyst` will allow the agent to self-correct based on execution feedback.

**Configuration:**
*   **Base:** V27 (BaseAgent inheritance, Index Retrieval).
*   **Modifications:**
    *   **LoopAgent:** Wraps `[solver_agent, code_based_runner, run_analyst]`.
    *   **RunAnalyst:** New agent that checks `run_output`. If successful, calls `exit_loop`. If failed, generates feedback.
    *   **Solver Instructions:** Updated to read `analysis_feedback` and `agent_code` from the previous iteration to perform repairs.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "fix_errors" --generator-filter "ADK_STATISTICAL_V28"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V28 | ADK_STATISTICAL_V27 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Fix Errors)** | TBD | 50.0% | TBD |
| **Avg Tokens/Turn** | TBD | ~14k | TBD |

## 3. Analysis
*   **Expected Behavior:** The agent should now be able to recover from simple Pydantic validation errors (like passing extra args to `SequentialAgent`) by seeing the error message and removing the offending argument in the next loop iteration.

## 4. Conclusion & Next Steps
*   Run the benchmark and analyze traces.
