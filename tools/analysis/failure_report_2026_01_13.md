# Tool Failure & Deep Dive Analysis Report

**Date:** 2026-01-13
**Subject:** Analysis of ADK Knowledge Agent Failures (V37-V41)

## 1. Executive Summary
This report analyzes recent failures in the `api_understanding` benchmark suite, focusing on tool usage patterns and root causes. The primary failure mode identified is **"Reasoning: Ignored Context (Hallucination)"**, where the agent successfully retrieves relevant information (or attempts to) but fails to incorporate it into the final answer, or gives up too early when initial searches fail.

## 2. Failure Statistics (N=41)
*   **Top Tool Used:** `get_module_help` (116 calls) - The agent is actively trying to fetch documentation.
*   **Primary Failure Mode:** `Hallucination` (13 cases) & `Unknown` (23 cases - likely complex reasoning failures).
*   **Context Quality:** In 40/41 cases, the LLM perceived the context as "Good", yet the agent still failed. This points to a **reasoning/attention deficit** rather than a retrieval deficit.

## 3. Deep Dive into Specific Failures

### Pattern A: The "Grep & Give Up" Loop (V41)
In V41, the agent frequently attempts to `grep` for concepts (e.g., "sequence of agents") but receives empty results or truncated output, and then fails to pivot to a broader search.

*   **Case:** "Which class is used to define a sequence of agents?"
    *   **Action:** `grep -r 'sequence of agents'` -> Output: `...` (likely unrelated or empty).
    *   **Follow-up:** `FETCH 'google.adk.agents.LoopAgent'`.
    *   **Error:** The agent guessed `LoopAgent` (which loops) instead of `SequentialAgent` (which sequences).
    *   **Insight:** The agent is checking for specific *phrases* in the code rather than searching for *concepts* or browsing the file tree.

### Pattern B: The "Context Blindness" (V37/V41)
In multiple cases, the agent successfully fetched the correct module but still hallucinated the answer.

*   **Case:** "Which parameter forces an `LlmAgent` to return a structured JSON object?"
    *   **Tools:** `FETCH 'google.adk.agents.llm_agent'` (OK).
    *   **Outcome:** The docstring likely contained `response_format` or `output_schema`, but the agent answered incorrectly (possibly `json_mode` or similar).
    *   **Root Cause:** The `get_module_help` output might be too dense, or the model (`flash`) is struggling to extract specific parameter names from long class definitions.

### Pattern C: Hallucinating Non-Existent Classes
*   **Case:** "Which class is used to run multiple agents concurrently?"
    *   **Action:** `SEARCH 'AgentGroup'` -> Empty.
    *   **Follow-up:** `FETCH 'agents.core.agent_group.AgentGroup'`.
    *   **Error:** It tried to fetch a class it just failed to find.
    *   **Insight:** The agent has a strong prior belief (likely from other frameworks) that an `AgentGroup` class exists.

## 4. Recommendations

### 1. Improve Search Strategy
*   **Problem:** `grep` is brittle for conceptual queries.
*   **Fix:** Encourage `get_file_tree` usage first to map the territory, then `read_definitions` or `get_module_help` on likely candidates. "Map then Drill" is better than "Guess then Grep".

### 2. Refine `get_module_help`
*   **Problem:** Docstrings are too long/dense for Flash to reliably parse.
*   **Fix:** Ensure `get_module_help` returns a *structured* summary (e.g., list of parameters and their types) rather than just a raw text dump, or explicitly instruct the model to look for specific sections (Args, Returns).

### 3. Reasoning Guidelines (In-Context Learning)
*   **Problem:** Model bias overrides retrieved context.
*   **Fix:** As implemented in V42, explicit guidelines like "If you see X, do Y" or "Prefer ADK native classes over generic names" are crucial.
