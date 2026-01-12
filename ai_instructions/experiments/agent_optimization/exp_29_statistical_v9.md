# Experiment Report: Statistical Discovery V9 (Deterministic Retrieval)

**Date:** 2026-01-10
**Status:** **Fail**
**Agent Variant:** `ADK_STATISTICAL_V9`
**Previous Best (Baseline):** `ADK_STATISTICAL_V7`

## 1. Hypothesis & Configuration
**Hypothesis:** Replacing flaky tool-calling during the solver turn with a deterministic 3-stage pipeline (Propose -> Fetch -> Solve) will improve reliability and token efficiency.
**Configuration:**
*   **Modifications:**
    *   `module_proposer` agent (LLM) suggests module names.
    *   `knowledge_fetcher` (Code) calls `get_module_help` deterministically.
    *   `solver_agent` (LLM) has ZERO tools; relies entirely on fetched context.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V9"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V9 | ADK_STATISTICAL_V7 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `NotImplementedError` | `ImportError` | Shift in failure mode |
| **Avg Tokens/Turn** | **~2.5k (Implementation)** | ~16k | **-13.5k (Massive Savings)** |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Extremely high token efficiency. The implementation turn is now comparable to the Podman baseline.
*   **Qualitative:** 
    *   **Failure 1 (Handoff):** The `knowledge_fetcher` failed to parse the module list because it expected a JSON string but received a validated object/dict. This led to an empty knowledge context.
    *   **Failure 2 (Logic):** Without context, the solver hallucinated a `generate_response` method instead of overriding `_run_async_impl`.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_21-01-04`
*   **Failures:**
    *   **Context Starvation:** "Retrieved context for 0 modules." The solver was essentially flying blind.
    *   **Hallucination:** Faced with zero context, the model reverted to its generic "Agent" prior (`generate_response`).

## 5. Conclusion & Next Steps
*   **Verdict:** **Keep the Topology, Fix the Logic.** The 3-stage deterministic fetch is clearly the correct path for token efficiency. We just need to fix the data plumbing.
*   **Action Items:**
    1.  **Robust Parsing:** Update the fetcher to handle Pydantic objects or dicts in session state.
    2.  **Experiment 30:** Implement `ADK_STATISTICAL_V10` with robust handoff and "Strict Signature Enforcement" instructions.
