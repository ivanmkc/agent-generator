# Token Reduction Plan

Based on the detailed analysis of token usage (including tool breakdowns), the following areas have been identified as the primary consumers of tokens:

1.  **`candidate_creator`**: ~6.1M tokens (Mostly Text Generation).
2.  **`run_analysis_agent`**: ~3.5M tokens.
    -   **Critical Finding:** The single most expensive step type is `run_analysis_agent` calling `Tool: exit_loop` (532k tokens in one case). This confirms that the final step of the loop, which ingests the full execution logs to decide whether to exit, is extremely costly.
    -   Other high-cost tools: `read_file` (~775k), `get_module_help` (~715k).
3.  **`module_selector_agent`**: ~2.2M tokens.
    -   High usage in `search_files` (~743k) and `read_file` (~326k).

## Strategies

### 1. Truncate Execution Logs for `run_analysis_agent`
The `CodeBasedRunner` saves the full output of the agent execution to `session.state["run_output"]`. This output is then injected directly into the `run_analysis_agent`'s instruction.
This is the **highest priority** fix.

**Action:**
- Modify `CodeBasedRunner` (or the `run_adk_agent` tool in `adk_tools.py`) to truncate `run_output`.
- Limit to ~20,000 characters (approx. 5-7k tokens), keeping head and tail.

### 2. Optimize Knowledge Retrieval (`module_selector_agent`)
The `module_selector_agent` uses `search_files` and `read_file` extensively.
The `search_files` tool might be returning too many results or full file contents in some cases (though `ripgrep` usually limits line count, `glob` does not).

**Action:**
- Review `search_files` and `list_directory` tool implementations to ensure they have strict output limits (e.g., max 50 files, max 200 lines per file).
- In `DocstringFetcherAgent` (if used), ensure it doesn't fetch entire large modules if only docstrings are needed.

### 3. Review `candidate_creator` Context
The `candidate_creator` spends ~5.6M tokens on "Text Generation". This implies the *input prompt* (context) is very large, making every generation expensive.
The context includes `knowledge_context` and `implementation_plan`.

**Action:**
- Summarize `knowledge_context` before passing it to `candidate_creator`.
- Ensure `include_contents='none'` is effectively isolating the prompt context from growing history.
- Check if `candidate_creator` is re-reading the same large files repeatedly.

### 4. Efficient Tool Output
The tool breakdown shows `read_file` and `search_files` are costly across agents.

**Action:**
- Ensure `read_file` has a sensible default limit if not specified (though agents usually read full files).
- For `search_files`, ensure the output format is compact.

## Implementation Steps

1.  **Modify `benchmarks/answer_generators/adk_tools.py` / `adk_agents.py`**:
    -   Implement `run_output` truncation in `CodeBasedRunner`.
2.  **Verify**:
    -   Run a short benchmark to confirm token usage reduction.