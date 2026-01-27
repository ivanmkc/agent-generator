# Experiment Report: Statistical Discovery V27 (BaseAgent Fallback)

**Date:** 2026-01-10
**Status:** **PASS** (100% Success)
**Agent Variant:** `ADK_STATISTICAL_V27`
**Previous Best (Baseline):** `ADK_STATISTICAL_V14` (Architecture Pass)

## 1. Hypothesis & Configuration
**Hypothesis:** Explicitly instructing the agent to inherit from `BaseAgent` and **manually handle** extra arguments (like `model` and `instruction`) instead of passing them to `super().__init__` would bypass the Pydantic `ValidationError` caused by the `Agent`/`LlmAgent` inheritance ambiguity.
**Configuration:**
*   **Modifications:**
    *   Retrieval: Index-based (`base_agent`).
    *   Instructions: "Inherit `BaseAgent`. Call `super(name=name)`. Do NOT pass `model` to super."
    *   Logic: Input access (`ctx.user_content`) and Event construction (`types.Content`) retained from V22/V24.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V27"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V27 | ADK_STATISTICAL_V26 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | **100%** | 0% | **+100%** |
| **Error Type** | None | `ValidationError` | **Solved** |
| **Avg Tokens/Turn** | ~14k | ~14k | Stable |

## 3. Analysis of Success
*   **The Breakthrough:** The agent stopped fighting the framework. By inheriting from the minimal `BaseAgent` and handling the `model` argument locally (ignoring it, as permitted by the prompt), it satisfied both the Pydantic validation (which forbids extra args on `BaseAgent`) and the task requirements.
*   **Key Components:**
    1.  **Correct Type:** `-> BaseAgent` signature matched the inheritance.
    2.  **Correct Logic:** `AsyncGenerator` with `yield Event`.
    3.  **Correct Schema:** `Event` constructed with `google.genai.types.Content`.
    4.  **Correct Input:** Accessed `ctx.user_content.parts[0].text`.

## 4. Trace Analysis (The "How")
*   **Trace ID:** `benchmark_runs/2026-01-10_23-47-13`
*   **Execution:** The agent correctly reasoned: "BaseAgent does not accept model/instruction. Store them in self if needed."
*   **Generated Code:**
    ```python
    class LogicAgent(BaseAgent):
        def __init__(self, name: str):
            super().__init__(name=name)
            # model is ignored
    ```
    This code ran perfectly.

## 5. Conclusion & Next Steps
*   **Verdict:** **Golden Candidate.** `ADK_STATISTICAL_V27` is the robust architecture we've been searching for.
*   **Action Items:**
    1.  **Scale Up:** Run this generator against the full `fix_errors` suite to verify generalizability.
    2.  **Refine:** Considerations for cleaner prompt (reduce verbosity) now that the rules are proven.
