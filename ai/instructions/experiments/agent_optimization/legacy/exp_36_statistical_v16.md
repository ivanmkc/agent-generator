# Experiment Report: Statistical Discovery V16 (Canonical Import)

**Date:** 2026-01-10
**Status:** **Fail** (Schema Violation)
**Agent Variant:** `ADK_STATISTICAL_V16`
**Previous Best (Baseline):** `ADK_STATISTICAL_V14`

## 1. Hypothesis & Configuration
**Hypothesis:** Importing `BaseAgent` from its defining module (`google.adk.agents.base_agent`) would resolve the `AssertionError` seen in V14 while maintaining correct architecture.
**Configuration:**
*   **Modifications:**
    *   Instructions: "Canonical Imports (CRITICAL)".
    *   Retained V14's architecture.
*   **Command:** `bash notebooks/run_benchmarks.sh --suite-filter "debug" --generator-filter "ADK_STATISTICAL_V16"`

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V16 | ADK_STATISTICAL_V14 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | 0% |
| **Error Type** | `ValidationError` | `AssertionError` | **Regression** (Init args) |
| **Avg Tokens/Turn** | ~14k | ~14k | Stable |

## 3. Analysis vs. Previous Best
*   **Quantitative:** Stable.
*   **Qualitative:**
    *   **Regression:** The agent correctly inherited from `BaseAgent` but passed `instruction` and `model` to `super().__init__`.
    *   **Context Ignoring:** The agent reasoned that "BaseAgent constructor requires instruction and model" despite the fetcher (presumably) showing otherwise or the agent ignoring the lack of evidence.
    *   **Root Cause:** Strong prior bias that "All Agents need instructions".

## 4. Trace Analysis (The "Why")
*   **Trace ID:** `benchmark_runs/2026-01-10_22-33-02`
*   **Failures:**
    *   **Validation Error:** Pydantic strictly forbade the extra fields. The "Schema Guard" was in the prompt, but the agent's internal logic ("I must satisfy BaseAgent") overrode the external constraint ("Don't pass unlisted fields").

## 5. Conclusion & Next Steps
*   **Verdict:** **Force the Check.** We need to make the agent explicitly validate its arguments against the context *before* writing code.
*   **Action Items:**
    1.  **Validation Table:** Require the agent to output a table comparing "Fields I want to use" vs "Fields listed in Context".
    2.  **Experiment 37:** Implement `ADK_STATISTICAL_V17` with "Validation Table" protocol.
