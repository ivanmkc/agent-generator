# Post-Mortem: Why ADK_STATISTICAL_V30 Failed

**Date:** 2026-01-11
**Subject:** Deep Dive into Experiment 50 (Task Delegation Architecture)

## 1. The Symptom
The `ADK_STATISTICAL_V30` agent failed all benchmark cases with `FAIL_GENERATION` or `AttributeError`.
*   **QA Tasks:** Failed with "Validation Error: Field 'answer' missing".
*   **Coding Tasks:** Failed with "AttributeError: module 'fixed' has no attribute 'create_agent'".

## 2. The Architecture
V30 attempted to wrap specialized sub-agents (`CodeWriter`, `KnowledgeExpert`) inside `FunctionTool`s called by a `DelegatorAgent`.
*   **Delegator:** "Call `run_knowledge_expert` tool."
*   **Tool:** "Run `qa_agent` loop manually."
*   **QA Agent:** "Write answer to `output_key='candidate_response'`."
*   **SmartFinalizer:** "Read `candidate_response` from session state and format it."

## 3. The Root Cause: State Delta Loss
In the ADK, `LlmAgent` does **not** write directly to `session.state`. Instead, it emits an `Event` containing a `state_delta` (a dictionary of changes).

*   **Normal Flow (SequentialAgent/Runner):** The `Runner` or `SequentialAgent` iterates over the sub-agent's events and explicitly applies `event.actions.state_delta` to `session.state`.
*   **V30 Flow (Manual Execution):** The `FunctionTool` manually iterated over the sub-agent's events:
    ```python
    async for event in qa_agent.run_async(ctx):
        pass  # <--- CRITICAL FAILURE
    ```
    The tool consumed the events but **ignored** the `state_delta`. Therefore, `candidate_response` was never written to the session state.

## 4. The Consequence
1.  `qa_agent` generated the correct answer and put it in a `state_delta`.
2.  The `FunctionTool` discarded the delta.
3.  The tool returned `None` (or default error string) because `ctx.session.state.get("candidate_response")` was empty.
4.  `SmartFinalizer` saw empty input.
5.  `SmartFinalizer` produced a default/garbage response.
6.  Benchmark validation failed.

## 5. The Fix (Theoretical)
To make V30 work, the tool wrapper must act as a mini-runner:
```python
async for event in qa_agent.run_async(ctx):
    if event.actions and event.actions.state_delta:
        ctx.session.state.update(event.actions.state_delta)
```

## 6. Conclusion
The failure was an implementation detail of the "Agent-as-a-Tool" pattern, not a fundamental flaw in delegation. However, given the high success rate of V29 (75%), we have reverted to the simpler architecture.
