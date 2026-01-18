# Analysis Report: V46 vs V47 Performance Gap

## Executive Summary
**Experiment 66 (V46)** significantly outperformed **Experiment 67 (V47)** (90% vs 75%) on the API Understanding benchmarks. The primary driver of this gap is **Context Fidelity**. V46 maintains a full, raw conversation history ("Shared History") between retrieval and solving, whereas V47's architecture introduces **Information Loss** through summarization and potential **Routing Errors**.

## Architecture Comparison

| Feature | V46 (Ranked Index) | V47 (Hybrid Specialist) |
| :--- | :--- | :--- |
| **Strategy** | Single-Track Specialist | Routed Multi-Expert |
| **Context Flow** | **Shared History** (Raw Tool Outputs) | **Hybrid** (Shared for Knowledge, Isolated for Coding) |
| **Retrieval** | Interactive (Browse/Search/Inspect) | Interactive (Knowledge) / Loop+Summarize (Coding) |
| **Data Fidelity** | **100%** (Solver sees exact docstrings) | **Variable** (Coding Expert sees only summaries) |

## Root Cause Analysis

### 1. The "Summary Trap" (Context Fidelity)
The most critical factor is how the agent consumes retrieval results.

*   **V46 (Winner):** The `SingleStepSolver` looks at the **conversation history**. When the retrieval agent calls `inspect_fqn`, the *entire* raw output (complete docstrings, every parameter, full signatures) is visible to the Solver. This allows it to answer questions that depend on specific phrasing (e.g., "short-circuit") or obscure parameter details.
*   **V47 (Loser):** While V47's *Knowledge Expert* was reverted to use Shared History, the *Coding Expert* relies on **Isolated State**. Its retrieval loop must compress findings into a `knowledge_context` summary string.
    *   **The Failure Mode:** If the Router sends an API question to the Coding Expert (e.g., because it involves "configuring" something), the retrieval loop might summarize the `BasePlugin` docstring as *"Handles plugin lifecycle callbacks"* instead of retaining the exact sentence *"returns a value to short-circuit execution"*. The downstream agent effectively "forgets" the specific detail needed to answer the question.

### 2. Routing Misclassification
V47 introduces a `RoutingDelegator` which adds a point of failure.
*   **False Positives for Coding:** Questions like *"How do I configure..."* or *"Which class is used..."* can be misinterpreted as implementation requests.
*   **Impact:** If a Knowledge question is routed to the **Coding Expert**, it suffers from the "Summary Trap" described above, leading to lower accuracy compared to V46 which always uses the high-fidelity path.

### 3. Agent Overhead
V47 involves a deeper chain of agents (Router -> Expert -> Planner -> ...). Each step consumes tokens and introduces a small probability of instruction drift or hallucination. V46 is a flat, efficient sequence (`Retrieval` -> `Solver`), minimizing the "telephone game" effect.

## Conclusion
For **API Understanding** and **Knowledge Retrieval** tasks, **Raw Context (Shared History)** is strictly superior to **Summarized Context**. The ability to "see" the exact source material is non-negotiable for high-precision QA.

**Recommendation:**
Future architectures should prioritize **Shared History** for all analysis tasks. If isolation is required for loop control (as in the Coding Expert), the "State Object" passed to the inner loop must include the **Raw Retrieval Logs**, not just a summary.
