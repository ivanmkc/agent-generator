# ADK-Based Agents for Benchmarking

This document details the architecture and implementation of the Google ADK (Agent Development Kit) agents used within the benchmarking framework. These agents are designed to autonomously solve software engineering tasks by exploring a codebase, planning, implementing solutions, and verifying them.

## Overview

The ADK-based agents utilize a **Structured Workflow** architecture. This design prioritizes:
1.  **State-Centric Communication:** Agents pass data (workspace paths, plans, code) via the session state (`ctx.session.state`) rather than conversation history. This is achieved by using **dedicated tools** (e.g., `save_implementation_plan`) instead of relying on implicit output schema parsing, which significantly reduces token usage and improves reliability.
2.  **Hybrid Logic:** Combines **LLM Agents** (for creative reasoning, planning, and coding) with **Code-Based Agents** (for deterministic tasks like setup, execution, and teardown).
3.  **Robust Verification:** Features an implementation loop that actively verifies generated code against a test plan before finalizing the solution.

## Architecture: `StructuredWorkflowAdk`

The core agent is a `SequentialAgent` composed of several specialized sub-agents. The flow is as follows:

1.  **`SetupAgentCodeBased`** (Code-Based)
    *   **Goal:** Prepare the isolated workspace.
    *   **Actions:** Creates a unique temporary directory (e.g., `task_uuid`), saves it to session state, and captures the user request.

2.  **`PromptSanitizerAgent`** (LLM)
    *   **Goal:** Cleanse the user input.
    *   **Actions:** Rewrites the user request to remove explicit tool-calling instructions (e.g., "Use the write_file tool to..."), ensuring the downstream agents focus on the *goal* rather than the *mechanics*.

3.  **`ModuleSelectorAgent`** (LLM + Code-Based Helper)
    *   **Goal:** Fetch relevant API documentation.
    *   **Modes:**
        *   **Index-Based (Default):** Uses `adk_index.yaml` to identify relevant modules and fetches their help strings programmatically. Efficient and targeted.
        *   **Tool-Based (Baseline):** Uses search tools (`grep`, `find`) to discover information. Slower but more flexible for unknown codebases.

4.  **`DocstringFetcherAgent`** (Code-Based)
    *   **Goal:** Retrieve the actual documentation content.
    *   **Actions:** Fetches docstrings for the modules identified by the `ModuleSelectorAgent`.

5.  **`Planner`** (LLM)
    *   **Goal:** Formulate a strategy.
    *   **Actions:** Analyzes the sanitized request and retrieved knowledge.
    *   **Key Tools:**
        *   `save_implementation_plan`: Saves the step-by-step plan text to state.
        *   `save_verification_plan`: Saves the test prompt to state.

7.  **`Implementation Loop`** (LoopAgent)
    *   Iterates (default max 1-5 times) until verification passes.
    *   **`CandidateCreator`** (LLM):
        *   Reads the plan or previous error logs.
        *   Outputs its rationale as natural text, followed by the complete Python code within a markdown block (` ```python...``` `).
        *   Uses `output_key="candidate_response"` to save this entire text to session state.
    *   **`CodeBasedRunner`** (Code-Based):
        *   **Goal:** Parse, Save, and Execute.
        *   **Actions:** 
            *   Retrieves `candidate_response` from session state.
            *   Robustly extracts the Python code (handling markdown blocks for `python`, `json`, or generic text).
            *   Saves the extracted code to `ctx.session.state["agent_code"]`.
            *   Executes the agent using `run_adk_agent` (a sandboxed runner) against the verification plan.
            *   Saves the execution logs to session state and yields them to the conversation history.
    *   **`RunAnalysisAgent`** (LLM):
        *   **Goal:** Verify success.
        *   **Actions:** Reads the logs from the `CodeBasedRunner` and the verification plan.
        *   If successful, calls `exit_loop`.
        *   If failed, outputs an analysis for the next `CandidateCreator` iteration.

8.  **`CodeBasedFinalVerifier`** (Code-Based)
    *   **Goal:** Persist the final solution.
    *   **Actions:** Writes the in-memory agent code to the final output file (e.g., `my_agent.py`) and formats the final response.

8.  **`CodeBasedTeardownAgent`** (Code-Based)
    *   **Goal:** Cleanup.
    *   **Actions:** Deletes the temporary workspace directory.

### `adk_agents.py`
Contains the definitions for all agent classes.
*   **`SetupAgentCodeBased`**, **`CodeBasedRunner`**, etc.: Python classes inheriting from `Agent` that implement `_run_async_impl` directly.
*   **`create_structured_adk_agent`**: The factory function that assembles the pipeline.

### `adk_tools.py`
Provides the toolset used by the agents.
*   **Async Shell:** `run_shell_command` is optimized for async execution using `asyncio` and `subprocess`.
*   **`get_module_help`**: A crucial tool that dynamically imports a python module and returns its docstrings and signature, allowing agents to "read" the API without reading raw source files.
*   **`run_adk_agent`**: A specialized tool that runs another ADK agent process, handling the complexity of `venv` activation and API key injection.

### `adk_schemas.py`
Defines the Pydantic models for structured communication (primarily used for internal type validation now, rather than strict output forcing).
*   **`SetupContext`**: Passes workspace and request info.
*   **`Plan` / `VerificationPlan`**: Structured output from the Planner.
*   **`RelevantModules`**: Output for the index-based retrieval.

## Usage & Configuration

Two primary factory functions expose these agents for benchmarking:

1.  **`create_structured_workflow_adk_generator`**
    *   Creates the fully optimized agent using Index-Based Knowledge Retrieval.
    *   Best for speed and reliability.

2.  **`create_baseline_workflow_adk_generator`**
    *   Creates the same agent but with Tool-Based Knowledge Retrieval.
    *   Used as a baseline to measure the impact of the optimized retrieval strategy.

## State Management
To minimize context window usage, these agents heavily rely on `ctx.session.state`.
*   **`workspace_dir`**: The root of the temporary environment.
*   **`implementation_plan`**: The text plan generated by the Implementation Planner.
*   **`verification_plan`**: The text verification plan generated by the Verification Planner.
*   **`candidate_response`**: The raw text output from `CandidateCreator` (containing rationale and code).
*   **`agent_code`**: The clean Python code extracted by `CodeBasedRunner`.
*   **`run_output`**: Logs from the last test run.