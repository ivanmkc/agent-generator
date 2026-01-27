# Experiment Report: Statistical Discovery V20 (Convergence)

**Date:** 2026-01-10
**Status:** **Fail** (Constructor Logic)
**Agent Variant:** `ADK_STATISTICAL_V20`
**Previous Best (Baseline):** `ADK_STATISTICAL_V14`

## 1. Hypothesis & Configuration
**Hypothesis:** Combining Markdown output, correct `Event` usage, and enforced async generator implementation would solve the LogicAgent task.
**Configuration:**
*   **Modifications:**
    *   Instructions: "Yield `Event`", "Override `_run_async_impl`", "Inherit `Agent`".
    *   Validation Table retained.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V20"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V20 | ADK_STATISTICAL_V14 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `AttributeError` (name) | `AssertionError` | **Regression** (Init) |
| **Avg Tokens/Turn** | ~14k | ~14k | Stable |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Stable.
*   **Qualitative:**
    *   **Logic Success:** The agent correctly implemented `_run_async_impl` as an async generator yielding `Event` objects. This is a major win over V19.
    *   **Constructor Failure:** The agent failed to call `super().__init__(name=name)`.
    *   **Reasoning:** It claimed `BaseAgent` definition was missing (true, fetcher failed) and decided to skip the super call, manually setting `self._name`. This broke Pydantic initialization.

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_22-54-18`
*   **Failures:**
    *   **Defensive Coding Gone Wrong:** The agent tried to be too defensive by not calling a "missing" constructor, unaware that Pydantic models require initialization.

## 5. Conclusion & Next Steps
*   **Verdict:** **Force Super Call.**
    *   The Logic is perfect. The Format is perfect.
    *   We just need to mandate `super().__init__(name=name)`.
*   **Action Items:**
    1.  **Instruction:** "You MUST call `super().__init__(name=name)`."
    2.  **Experiment 41:** Implement `ADK_STATISTICAL_V21`.
