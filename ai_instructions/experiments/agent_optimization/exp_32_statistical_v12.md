# Experiment Report: Statistical Discovery V12 (Context-Aware Retrieval)

**Date:** 2026-01-10
**Status:** **Fail**
**Agent Variant:** `ADK_STATISTICAL_V12`
**Previous Best (Baseline):** `ADK_STATISTICAL_V11`

## 1. Hypothesis & Configuration
**Hypothesis:** Explicitly ensuring the ADK library is in the search path for the deterministic fetcher will resolve the retrieval failures and provide the solver with necessary API truth.
**Configuration:**
*   **Modifications:**
    *   `ContextAwareKnowledgeAgent`: Logic added to handle runtime fallback (though still restricted by `get_module_help`'s internal logic).
    *   Added "No Hallucinations" and "Missing Classes" rules to solver.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V12 | ADK_STATISTICAL_V11 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `ValidationError` (`instruction`) | `ImportError` | Regressed to V10 logic |
| **Avg Tokens/Turn** | ~14k | ~14k | Stable |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Token usage remains optimized.
*   **Qualitative:** 
    *   **Retrieval Failure:** `Retrieved context for 0/2 modules.` 
    *   **RCA:** The agent proposed `google.adk.agents.BaseAgent`. `importlib.import_module` (used in the fetcher) fails on class paths. It only works on module paths.
    *   **Logic Regression:** Because the context was empty, the solver defaulted to its training data bias, hallucinating that `BaseAgent` accepts `instruction` and `model`.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_21-32-21`
*   **Failures:**
    *   **The "Import Depth" Trap:** We are asking the model to propose module paths, but it's proposing class paths. The deterministic fetcher is too rigid to handle the leaf nodes.

## 5. Conclusion & Next Steps
*   **Verdict:** **Fix the Fetcher.** The 3-stage pipeline is correct, but the "Deterministic" part needs to be smarter about Python imports.
*   **Action Items:**
    1.  **Smart Fetcher:** Implement `SmartKnowledgeAgent` that attempts to import the parent module if a leaf import fails, and then searches for the class within it.
    2.  **Experiment 33:** Implement `ADK_STATISTICAL_V13` with robust class-aware retrieval.
