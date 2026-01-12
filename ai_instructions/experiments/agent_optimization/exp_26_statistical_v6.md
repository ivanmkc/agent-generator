# Experiment Report: Statistical Discovery V6 (Strict Signature Compliance)

**Date:** 2026-01-10
**Status:** **Fail**
**Agent Variant:** `ADK_STATISTICAL_V6`
**Previous Best (Baseline):** `ADK_STATISTICAL_V5`

## 1. Hypothesis & Configuration
**Hypothesis:** Explicitly warning about the `AsyncGenerator` vs `Coroutine` distinction and enforcing `yield` statements will resolve the `TypeError` observed in previous iterations.
**Configuration:**
*   **Modifications:**
    *   Added "STRICT SIGNATURE COMPLIANCE" section to instructions.
    *   Mandated `yield` for `AsyncGenerator` methods.
    *   Re-emphasized `search_files` for every import.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V6 | ADK_STATISTICAL_V5 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `TypeError` (BaseModel positional) | `ImportError` | Shift in failure mode |
| **Avg Tokens/Turn** | ~11k | ~18k | **-7k (Improved Efficiency)** |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Token usage continue to drop (now ~11k). The prompt is getting more "surgical".
*   **Qualitative:** 
    *   The agent successfully implemented `_run_async_impl` with `yield`, resolving the `AsyncGenerator` error.
    *   It successfully found the imports (no `ModuleNotFoundError`).
    *   **New Blocker:** It called `super().__init__(name)` instead of `super().__init__(name=name)`. Pydantic (BaseModel) requires keyword arguments for field initialization.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_20-33-08`
*   **Failures:**
    *   **Positional Argument Trap:** Despite knowing `name` is required, the model defaulted to the standard Python `__init__` pattern (`super().__init__(arg)`) rather than Pydantic's kwarg-only pattern.
    *   **Root Cause:** The `get_module_help` output showed `BaseAgent(*, name: str, ...)` where the `*` indicates keyword-only, but the model ignored this syntactic hint.

## 5. Conclusion & Next Steps
*   **Verdict:** **Iterate**. We are now one "keyword" away from a passing benchmark.
*   **Action Items:**
    1.  **Pivot:** Explicitly mandate keyword-only initialization for Pydantic models.
    2.  **Experiment 27:** Implement `ADK_STATISTICAL_V7` with "Pydantic Kwarg Enforcement".
