# Fix Report: StructuredWorkflowAdk Stabilization

**Date:** December 28, 2025
**Status:** Resolved

## 1. Executive Summary
The `StructuredWorkflowAdk` benchmark generator was failing consistently due to a combination of resource exhaustion (rate limits, context window limits), connection management errors, and missing tool definitions. A comprehensive refactoring of the agent's infrastructure and toolset was performed to address these issues.

## 2. Issues & Root Causes

### A. Resource Exhaustion (429 & 400 Errors)
*   **Symptoms:** `429 RESOURCE_EXHAUSTED` (Rate Limit) and `400 INVALID_ARGUMENT` (Context Window Exceeded > 1M tokens).
*   **Cause:**
    *   **Rate Limits:** The generator was using a single static API key for all concurrent tasks, ignoring the `ApiKeyManager` pool.
    *   **Context Explosion:** The `StructuredWorkflowAdk` passes accumulated context (search results, file contents) through multiple sub-agents. Unbounded `search_files` (grep) and `read_file` results were bloating the context beyond 1 million tokens.

### B. Connectivity Failures (aiohttp AssertionError)
*   **Symptoms:** `AssertionError: self._connector is not None` in `aiohttp`.
*   **Cause:** The initial fix for key rotation created a new `google.genai.Client` for every request. This broke `aiohttp`'s session management, as sessions were not being reused or closed properly.

### C. Tool Execution Failures
*   **Symptoms:** `ValueError: Tool 'run_adk_agent' not found` and `Tool 'list_models' not found`.
*   **Cause:**
    *   **Prompt Injection:** The benchmark prompt ("FIRST, use the run_adk_agent tool...") was being passed raw to sub-agents (`KnowledgeRetrieval`, `Planner`) which did not have that tool, causing them to hallucinate execution attempts.
    *   **Missing Tools:** The `CandidateCreator` and `Verifier` agents initially lacked access to the raw `run_adk_agent` tool required to satisfy the strict prompt instructions.

### D. Implementation Bugs
*   **Symptoms:** `NameError: name 'os' not defined`, `AttributeError: 'Content' object has no attribute 'text'`.
*   **Cause:** Missing imports and incorrect assumption about `google.genai` response object structure in logging code.

## 3. Applied Fixes

### Infrastructure
1.  **RotatingKeyGemini with Caching:** Implemented a custom `RotatingKeyGemini` model class that:
    *   Rotates API keys per request using `ApiKeyManager`.
    *   **Caches `Client` instances** by API key to ensure `aiohttp` sessions are persistent and thread-safe.
2.  **Environment Variable Injection:** Updated `AdkTools.run_adk_agent` to inject the current API key into the subprocess environment, ensuring the *verified agent* also uses a rotated key.

### Agent Architecture
1.  **Context Hygiene:**
    *   Modified `read_file` tool to default to a **200-line limit** (down from unlimited).
    *   Modified `search_files` tool to limit output to **50 matches**.
    *   These changes prevent accidental context explosion from large files or broad searches.
2.  **Prompt Sanitization:**
    *   Introduced `sanitized_user_request` in `SetupContext`.
    *   Updated `SetupAgent` to strip tool-calling instructions from the request before passing it to downstream agents.
    *   Hardened `KnowledgeRetrievalAgent` instructions to ignore execution requests.
3.  **Tool Availability:**
    *   Restored `run_agent_tool` access for `CandidateCreator` and `Verifier` to allow them to satisfy imperative user prompts if necessary.

### Code Quality
1.  Fixed all `NameError` and `AttributeError` bugs.
2.  Updated unit tests (`test_adk_tools.py`, `test_cloud_run_generator_unit.py`) to reflect changes and fix broken mocks.

## 4. Verification
*   **Unit Tests:** All unit tests in `benchmarks/tests/unit/test_adk_tools.py` pass.
*   **Integration:** The `debug_suite` benchmark for `StructuredWorkflowAdk` now runs without crashing (no traceback), successfully initiating tool calls and progressing through the workflow.
