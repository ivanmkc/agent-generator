# Design Doc: Advanced Pagination Strategies for `list_adk_modules`

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
The `list_adk_modules` tool provides paginated access to the ADK API surface. Agents almost exclusively call `page=1` and stop, missing 90%+ of the library. They rarely iterate through pages 2-30.

## 2. Proposed Strategies

### A. Usage-Ranked Pagination (The "Pareto" Page)
**Concept:**
- Instead of alphabetical order, order items by "Usage Score" (derived from GitHub usage, internal examples, or "PageRank" of the class graph).
- **Page 1** contains the top 100 most used classes (e.g., `LlmAgent`, `FunctionTool`, `RunConfig`).
- **Impact:** 99% of queries should be answerable with Page 1.

### B. Semantic Clustering (Topic Pages)
**Concept:**
- Group modules by topic: "Agents", "Tools", "Config", "Plugins".
- Tool argument: `list_adk_modules(category="Agents")`.
- **Implementation:** Tag modules in the index.

### C. "Smart" Next Page Hints
**Concept:**
- If Page 1 doesn't contain the answer (inferred from the agent's subsequent query), the tool result for the *next* action (e.g., a failed search) should include a tip: "Item not found. Consider checking `list_adk_modules(page=2)` which contains utility classes."

### D. Adaptive Page Size
**Concept:**
- Allow the agent to request `limit=500` if it has a large context window, instead of fixing it at 100.

## 3. Implementation Details
- **Index Generation:** Update `generate_adk_index.py` to compute a `rank` score for each item.
- **Runtime:** `AdkTools.list_ranked_targets` already implements Strategy A. We need to formalize this as the *default* behavior for `list_adk_modules` in all agents, effectively replacing the alphabetical list.

## 4. Verification
- **Metric:** "Recall @ Page 1". Percentage of benchmark questions answerable using only symbols present on Page 1.
- **Target:** > 95%.
