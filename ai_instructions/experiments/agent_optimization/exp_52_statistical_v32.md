# Experiment Report: Statistical Discovery V32 (AgentTool Encapsulation)

**Date:** 2026-01-11
**Status:** **Pending**
**Agent Variant:** `ADK_STATISTICAL_V32`
**Previous Best (Baseline):** `ADK_STATISTICAL_V29` (Coding Specialist)

## 1. Hypothesis & Configuration
**Hypothesis:** Wrapping the successful `ADK_STATISTICAL_V29` agent entirely within an `AgentTool` will allow a parent `Delegator` agent to invoke it as a single unit of work. This provides a robust "Agent-as-a-Service" pattern where the Delegator handles the high-level request and V29 handles the complex execution logic (Setup -> Retrieval -> Loop -> Teardown) in isolation.

**Configuration:**
*   **Base Logic:** `ADK_STATISTICAL_V29` (imported wholesale).
*   **Encapsulation:** `AgentTool(agent=v29_agent, include_plugins=True)`.
*   **Topology:** `SequentialAgent([Delegator])`. The Delegator calls the tool.
*   **Expected Outcome:** The Delegator should call the tool, V29 should execute its full lifecycle (creating its own temp workspace), and return the result string.

## 2. Results Comparison
| Metric | ADK_STATISTICAL_V32 | ADK_STATISTICAL_V29 | Change |
| :--- | :--- | :--- | :--- |
| **Pass Rate (Debug)** | TBD | 66.7% | TBD |
| **Coding Task** | TBD | Pass | TBD |
| **QA Tasks** | TBD | Fail | TBD |

## 3. Analysis
*   **Focus:** Verify that state propagation and workspace isolation function correctly when nested inside an `AgentTool`.

## 4. Conclusion & Next Steps
*   Run the benchmark.
