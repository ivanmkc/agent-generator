# Experiment Report: Statistical Discovery V5 (Optimized Tools)

**Date:** 2026-01-10
**Status:** **Fail**
**Agent Variant:** `ADK_STATISTICAL_V5`
**Previous Best (Baseline):** `ADK_STATISTICAL_V3`

## 1. Hypothesis & Configuration
**Hypothesis:** Replacing raw `read_file` with `read_definitions` (AST-based) and enforcing the "Proof of Knowledge" protocol will focus the agent on structural truth and prevent hallucinated imports/attributes.
**Configuration:**
*   **Modifications:**
    *   Enabled `read_definitions`.
    *   Updated instructions to explicitly prohibit raw file reading.
    *   Mandated "quoting" of discovered signatures in reasoning.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V5 | ADK_STATISTICAL_V3 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `ImportError` (`Response`) | `AttributeError` (`.input`) | Reverted to import issues |
| **Avg Tokens/Turn** | ~18k | ~47k | **-29k (Huge Efficiency Win)** |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Dramatic reduction in token usage (from 47k to 18k). The "Proof of Knowledge" and `read_definitions` approach is significantly more efficient.
*   **Qualitative:**
    *   **V3:** Attempted to use logic but guessed `.input`.
    *   **V5:** Correctly identified that it needed specific types, but hallucinated that `Response` exists in `google.adk.agents`.
    *   **Regression:** By focusing on types, the agent became more sensitive to import paths, which it is still guessing.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_20-25-59`
*   **Failures:**
    *   **Import Guessing:** The agent saw `InvocationContext` and `Event` in the tools, but then assumed `Response` was also in the same module.
    *   **Tool Misuse:** It did not use `search_files` to verify *where* `Response` was defined; it simply added it to the `from google.adk.agents import ...` block.
    *   **The "Generator" Trap:** In V3, the agent encountered `TypeError: 'async for' requires an object with __aiter__ method, got coroutine`. This is because `_run_async_impl` MUST be an `AsyncGenerator` (yielding events), but the agent implemented it as a standard `async def` (returning a value).

## 5. Conclusion & Next Steps
*   **Verdict:** **Iterate**. The efficiency win is massive (60% token reduction), but accuracy is blocked by import and signature nuances.
*   **Action Items:**
    1.  **Pivot:** We need to solve the `AsyncGenerator` vs `Coroutine` confusion.
    2.  **Constraint:** Add a rule: "If a method signature returns `AsyncGenerator`, you MUST use `yield`, not `return`."
    3.  **Experiment 26:** Implement `ADK_STATISTICAL_V6` with "Strict Signature Compliance" and a warning about `AsyncGenerator` syntax.
