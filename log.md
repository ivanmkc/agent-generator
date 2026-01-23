# Test & Benchmark Report: Ranked Knowledge Runner (MCP V47)

**Date:** 2026-01-23
**Focus:** Integration Testing and Benchmarking of `mcp_adk_agent_runner_ranked_knowledge`.

## 1. Unified Integration Test Results

**Command:** `pytest benchmarks/tests/integration/test_unified_generators.py -k podman_mcp_adk_runner_ranked_knowledge_test_case`

| Test Case | Result | Notes |
| :--- | :--- | :--- |
| `test_generator_capabilities` | **PASSED** | Correctly identified MCP server `adk-knowledge` after refactoring capability check to use `get_mcp_servers()`. |
| `test_generator_execution` | **PASSED** | Successfully generated an answer for case `test:mcp_adk_runner`. Trace logs confirmed successful execution. |
| `test_generator_memory_context` | **SKIPPED** | No expected context files defined for this case. |

**Assessment:** The generator and the test harness are now fully functional and consistent.

## 2. Benchmark Run Results (Debug Suite)

**Command:** `python notebooks/run_benchmarks.py --suite-filter debug --generator-filter ranked_knowledge`

### Generator: `ranked_knowledge_bm25` (gemini-2.5-pro)
*   **Total:** 3 Tests
*   **Passed:** 3 (100%)
*   **Failed:** 0

| Benchmark Case | Result | Time |
| :--- | :--- | :--- |
| `mc_proactivity` | PASS | 14.30s |
| `api_understanding_base_agent` | PASS | 25.51s |
| `fix_error_logic_agent` | PASS | 50.84s |

### Generator: `ranked_knowledge_keyword` (gemini-2.5-pro)
*   **Total:** 3 Tests
*   **Passed:** 2 (66.7%)
*   **Failed:** 1

| Benchmark Case | Result | Time | Notes |
| :--- | :--- | :--- | :--- |
| `mc_proactivity` | PASS | 14.40s | |
| `api_understanding_base_agent` | PASS | 19.73s | |
| `fix_error_logic_agent` | **FAIL (Validation)** | 59.66s | **Syntax Error:** Generated code contained `def def create_agent...`. This indicates a minor hallucination in the `fix_error` logic for the keyword variant. |

## 3. Conclusion

The `mcp_adk_agent_runner_ranked_knowledge` is working correctly in its primary BM25 configuration, achieving a 100% pass rate on the debug suite. The `keyword` variant showed a regression in code syntax generation. 

**Fixes Applied:**
*   Refactored `GeminiCliAnswerGenerator.get_mcp_tools` to `get_mcp_servers` to align with CLI output format and semantic meaning.
*   Updated integration tests to assert on server names rather than ambiguous tool lists.