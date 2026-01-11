# Experiment Report: [Experiment Name]

**Date:** YYYY-MM-DD
**Status:** [Success / Fail / Inconclusive]
**Agent Variant:** [e.g., ADK_STATISTICAL_V2]
**Previous Best (Baseline):** [e.g., ADK_REACT]

## 1. Hypothesis & Configuration
**Hypothesis:** [What are you testing? e.g., "Enforcing strict type checking in instructions will reduce AttributeError rates."]
**Configuration:**
*   **Modifications:** [List key changes from the baseline]
*   **Command:** `bash notebooks/run_benchmarks.sh --generator-filter "NEW_VARIANT|BASELINE"`

## 2. Results Comparison
| Metric | New Variant | Previous Best | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | 0% | 0% | [e.g., +10%] |
| **Pass Rate (Fix Errors)** | 0% | 0% | [e.g., -5%] |
| **Avg Tokens/Turn** | 0 | 0 | [e.g., -2.5k] |

## 3. Analysis vs. Previous Best
*   **Quantitative:** [Did the pass rate improve? By how much? Did token usage drop?]
*   **Qualitative:** [Is the new variant "smarter" or just "cheaper"? Does it follow instructions better? Does it handle edge cases that the baseline missed?]
*   **Regressions:** [Did this fix one thing but break another? Detail any new failures that weren't present in the baseline.]

## 4. Trace Analysis (The "Why")
*   **Successes:** [What went right?]
*   **Failures:** [Detailed analysis of failure modes. Reference specific trace IDs or patterns.]

## 5. Conclusion & Next Steps
*   **Verdict:** [Keep / Revert / Iterate]
*   **Action Items:**
    1.  [e.g., "Promote NEW_VARIANT to current best"]
    2.  [e.g., "Investigate regression in case X"]