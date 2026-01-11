# Fix Report: Tool Calling Failures (Skipping Tools)

**Date:** December 27, 2025  
**Status:** Resolved

## 1. Executive Summary
This report details the resolution of a critical issue where benchmarked agents (`mcp_context7` and `mcp_adk_agent_runner`) were consistently skipping mandatory tool calls. The issue led to low benchmark accuracy as agents attempted to hallucinate answers or execute code without prior verification. The root cause was identified as a misconfiguration in how system instructions were loaded into the Gemini CLI environment, combined with insufficient prompt guidance. The issue was resolved by fixing Dockerfile environment variables and reinforcing prompt instructions.

## 2. Problem Description
During benchmark runs, two primary failure modes were observed:
*   **MCP Context7:** The agent was expected to use the `context7` tool to search the codebase but instead provided generic or hallucinated answers without invoking the tool.
*   **MCP ADK Runner:** The agent was expected to "research" (using `get_module_help` or `search_file_content`) before writing and executing ADK agent code. Instead, it would immediately call `run_adk_agent` with unverified code, leading to execution errors.

## 3. Root Cause Analysis
Investigation revealed two concurrent causes:

### A. Missing System Instructions (Infrastructure)
The Gemini CLI relies on the `GEMINI_SYSTEM_MD` environment variable to load system instructions.
*   **Finding:** In the Dockerfiles for `mcp_context7` and `mcp_adk_agent_runner`, this variable was either missing or set incorrectly (e.g., `GEMINI_SYSTEM_MD=true` without a corresponding `system.md` in the working directory, or pointing to a non-existent path).
*   **Impact:** The strong "You MUST use tools" instructions defined in the markdown files were never loaded into the model's context.

### B. Prompt Ambiguity (Prompt Engineering)
*   **Finding:** The `MCP_ADK_RUNNER_CASE` prompt instructed the agent to "complete this task" but did not explicitly enforce a *multi-step* process.
*   **Impact:** The model optimized for speed, skipping the research phase and jumping straight to execution, which is a common behavior when not strictly constrained.

## 4. Applied Fixes

### Infrastructure & Configuration
1.  **Context7 Fix:**
    *   Created `benchmarks/answer_generators/gemini_cli_docker/mcp_context7/system.md` with explicit tool usage directives.
    *   Updated `Dockerfile` to copy this file to `/root/.gemini/system.md` and set `ENV GEMINI_SYSTEM_MD=/root/.gemini/system.md`.

2.  **ADK Runner Refactoring:**
    *   Split the monolithic `mcp_adk_agent_runner` into `mcp_adk_agent_runner_basic` and `mcp_adk_agent_runner_smart_search` to better isolate behaviors.
    *   Updated both Dockerfiles to copy `INSTRUCTIONS.md` and set `ENV GEMINI_SYSTEM_MD=/workdir/INSTRUCTIONS.md`.

### Prompt Engineering
1.  **Benchmark Case Update:**
    *   Modified `MCP_ADK_RUNNER_CASE` in `predefined_cases.py`.
    *   **Old Prompt:** "1. Use run_adk_agent..."
    *   **New Prompt:** "1. FIRST, verify the correct imports and class signatures using available tools (e.g. `get_module_help` or search). 2. SECOND, use the `run_adk_agent` tool..."

## 5. Verification Results
Verification was performed using targeted integration tests.

*   **Test Case:** `podman_mcp_adk_runner_smart_search_test_case`
*   **Observation:** The trace logs confirmed that the agent now performs a `get_module_help` or `search_file_content` call *before* calling `run_adk_agent`.
*   **Test Case:** `podman_context7_test_case`
*   **Observation:** The agent successfully calls the `context7` tool to answer questions about the codebase.

## 6. Recommendations
*   **Continuous Monitoring:** Ensure `GEMINI_SYSTEM_MD` is correctly set for any new Docker-based agents.
*   **Prompt Robustness:** Continue to use "Chain of Thought" style prompts (Step 1, Step 2...) for complex tasks to prevent model "shortcut" behavior.
