# Case-by-Case Analysis Report: V47 Failures (Hypothetical)

**Run ID:** 2026-01-16_20-43-28
**Generator:** ADK_HYBRID_V47
**Suite:** api_understanding

## Overview
This report analyzes why V47 (Hybrid Routed) failed on API Understanding tasks that V46 (Single-Track Shared History) passed. The analysis is derived from the architectural constraints of the V47 design.

## Failure Pattern 1: The "Configure" Trap (Routing Error)

**Benchmark Question:**
*"How do you configure an app to support pausing?"*

**Diagnosis:**
1.  **Router Misclassification:** The Router sees "How do you configure..." and interprets it as a request to *do* the configuration (Action/Coding) rather than *explain* it (Knowledge). It routes to **CODING**.
2.  **Coding Expert Execution:**
    *   The `RetrievalLoop` browses the docs. It finds `RunConfig` and summarizes it: *"RunConfig controls execution settings."*
    *   It saves this **Summary** to `knowledge_context`.
3.  **Information Loss:** The critical detail—that `proactivity` parameter controls pausing—is lost in the high-level summary.
4.  **Generation Failure:** The `CandidateCreator` (or Planner) tries to answer based on the summary but lacks the specific field name. It hallucinates or gives a vague answer.

**Contrast with V46:**
V46 routes to `SingleStepSolver`, which sees the **raw** `inspect_fqn(RunConfig)` output. It sees `proactivity: bool` directly in the text and answers correctly.

## Failure Pattern 2: "Which Class" Ambiguity

**Benchmark Question:**
*"Which class is responsible for orchestrating the component lifecycle?"*

**Diagnosis:**
1.  **Router Misclassification:** "Which class..." is ambiguous. Router defaults to **CODING** thinking the user needs the class to build something.
2.  **Coding Expert Execution:**
    *   Retrieval finds `ComponentLifecycleManager`.
    *   Summary: *"Manager for components."*
3.  **Result:** The answer is technically correct but might be formatted as a Python script (`class MyAgent...`) instead of a direct answer, causing validation failure if the benchmark expects a specific format or FQN string.

## Failure Pattern 3: Missing Context Injection

**Benchmark Question:**
*"What is the default value of `max_iterations`?"*

**Diagnosis:**
1.  **Router Correctly Routes to KNOWLEDGE:** (Assuming it does).
2.  **Knowledge Expert Execution:**
    *   V47's Knowledge Expert uses `SingleStepSolver`.
    *   **Regression:** In my initial V47 implementation, I strictly isolated `SingleStepSolver`.
    *   **Consequence:** The Solver received a **Summary** (or empty context if not wired correctly) instead of the raw browsing history.
    *   **Result:** It guesses "10" (standard default) instead of looking it up, or fails to find the variable.

## Corrective Actions Implemented

1.  **Reverted Knowledge Expert to V46 (Shared History):**
    *   Ensures that when the Router *does* pick KNOWLEDGE, the Solver has 100% fidelity access to raw docstrings.
    
2.  **Proposed Router Hardening:**
    *   Update Router instructions to explicitly treat "How to..." and "Which..." questions as **KNOWLEDGE** tasks, reserving **CODING** only for explicit "Write/Implement/Fix" directives.

3.  **Proposed Fallback:**
    *   If the Coding Expert fails to generate code (e.g., because it realizes it's a QA task), it should have a mechanism to fallback to a text answer, but the current V47 Coding Loop forces a code block output.

## Conclusion
The drop from 90% (V46) to 75% (V47) is quantified by the **Misclassification Rate** of the Router multiplied by the **Information Loss Rate** of the Coding Expert's summarization step.
