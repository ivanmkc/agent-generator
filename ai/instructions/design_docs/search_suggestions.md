# Design Doc: "Did You Mean?" - Search Suggestions for Zero Results

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
When an agent searches for a typo (e.g., `ToolConfig` vs `ToolsConfig`) or a slightly incorrect name, `search_adk_knowledge` returns "No matches found." Agents often hallucinate a fix or give up, rather than retrying with a corrected query.

## 2. Proposed Solution
Implement a "Close Match" suggester that triggers when exact search returns 0 results.

### A. Levenshtein Distance (Fuzzy Matching)
- **Library:** `rapidfuzz` or `difflib`.
- **Logic:** Compare query against all known FQN parts.
- **Threshold:** Distance <= 2 edits.

### B. BM25 Relaxation
- If strict token matching fails, try relaxed matching (e.g., character n-grams) provided by `rank_bm25` or custom logic.

### C. Embedding-based Similarity (Semantic Fallback)
- If keyword search fails, use `semantic_search` (if embeddings available) to find conceptually similar items.

## 3. Tool Output Format
Instead of:
`"No matches found for 'ToolConfg'."`

Return:
```text
No exact matches found for 'ToolConfg'.
Did you mean:
1. google.adk.tools.ToolConfig (Score: 0.95)
2. google.adk.tools.function_tool.FunctionTool (Score: 0.4)
```

## 4. Implementation Steps
1.  **Modify `AdkTools.search_ranked_targets`:**
    - Capture empty result set.
    - If empty, call `_get_suggestions(query)`.
    - Format output string.
2.  **Implement `_get_suggestions`:**
    - Use `difflib.get_close_matches` against a cached list of all class names.
    - Fallback to BM25 with lower threshold?

## 5. Impact
- Reduces "Hallucination" failures where agent invents a class.
- Reduces "Retrieval: Zero Results" failures.
