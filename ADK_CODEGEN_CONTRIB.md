# ADK Code Generation: Project Overview & Contributor Guide

This doc summarizes the “ADK Code Generation” effort and provides a starting point for contributors.

## Project Summary
The **ADK Code Generation** project aims to build, evaluate, and optimize AI agents capable of writing, debugging, and understanding code using the **Google Agent Development Kit (ADK)**. We are building and comparing several candidate architectures—including custom ADK agents alongside `gemini-cli` based approaches. By leveraging specialized techniques such as Retrieval-Augmented Generation (RAG) with `adk-docs-ext`, execution feedback loops with `mcp_adk_agent_runner`, and semantic search with `context7`, we seek to create developer tools that significantly accelerate the adoption and usage of the ADK. The core of this effort involves a rigorous benchmarking framework to measure agent performance across API understanding, configuration, and code repair tasks.

---

## For contributors, here are potential tasks to pick up.

### 1. Generate more benchmark cases

**Current Setup:**
Our benchmarking infrastructure is built on a containerized environment using `gemini-cli` and `podman`. It is designed to compare off-the-shelf LLM configurations against **custom ADK-based agents** (e.g., `StructuredWorkflowAdk` and `BaselineWorkflowAdk`) that leverage the framework's own capabilities for code generation.

We currently run five primary suites:
*   **`api_understanding`**: Validates the model's recall of ADK class signatures and import paths.
*   **`fix_errors`**: Tests the ability to repair broken code snippets through reasoning and tool usage.
*   **Multiple Choice Suites**: `configure_adk_features_mc`, `diagnose_setup_errors_mc`, and `predict_runtime_behavior_mc` assess configuration knowledge and runtime prediction.

The current candidates already do quite well on the existing benchmark cases, which cover low-complexity use cases. We need to cover more complex cases.

*   **Expand `fix_errors` Suite:**
    *   **Current State:** 25 cases covering basic `LlmAgent` and `SequentialAgent` setups.
    *   **Task:** Add cases in `benchmarks/benchmark_definitions/fix_errors/cases/` that require fixing **multi-agent state management** issues (e.g., passing state correctly between agents in a `SequentialAgent`) and **plugin lifecycle hooks** (e.g., debugging a `BasePlugin` that fails during `before_agent_callback`).
*   **Expand `api_understanding` Suite:**
    *   **Task:** Add questions targeting advanced `ToolContext` usage (e.g., how to access session ID from a tool) and specific `Model` configuration parameters (e.g., `safety_settings` structure).
*   **New Benchmark Types:**
    *   **End-to-End Application Scaffolding**: Generate a fully functional multi-agent system from a high-level prompt.
    *   **Refactoring & Migration**: Convert legacy scripts or non-ADK code into idiomatic ADK patterns.
    *   **Integration Tests**: scenarios requiring the agent to wire up multiple tools and external APIs correctly.
*   **Automation:** Create an ADK agent to auto-generate new benchmark cases, with increasing complexity.
*   **Vetting:** Organize human vetting sessions with UX to verify benchmark accuracy and usefulness.

### 2. Clean up benchmark infra

Current infra is partially vibecoded and good use of an engineer's review with a fine-toothed comb. Focus areas include:

*   **Robust Error Parsing:**
    *   **Problem:** `PytestBenchmarkRunner.run_benchmark` currently relies on fragile regex to parse exception names from pytest's stdout.
    *   **Fix:** Refactor `benchmarks/benchmark_runner.py` to use `pytest`'s machine-readable output (e.g., `--junitxml` or JSON report) for reliable error categorization.
*   **Generalize Signature Verification:**
    *   **Problem:** `_verify_signature` in `benchmarks/benchmark_runner.py` is hardcoded to look for a function named `create_agent`.
    *   **Fix:** Make the entry-point function name configurable in the `benchmark.yaml` definition to support diverse test cases (e.g., class-based entry points).
*   **Standardize Orchestration:**
    *   **Problem:** Retry logic in `benchmarks/benchmark_orchestrator.py` is manual and tightly coupled with execution.
    *   **Fix:** Refactor to use a robust retry library (like `tenacity`) and decouple generation attempts from execution validation.

### 3. Improve code generation candidate quality

*   We have a PoC ADK agent (`StructuredWorkflowAdk`) that writes ADK code.
*   **Technical challenges:**
    *   **Reduce Token Usage:** Implement `include_contents='none'` for stateless upstream agents (like the Planner or Researcher) in `benchmarks/answer_generators/adk_agents.py` to prevent passing full conversation history where it's not needed.
    *   **Improve Code Quality:** Ensure the generated code follows ADK best practices (e.g., using `FunctionTool` decorators correctly).
    *   **Enhance Self-Correction:** Improve the feedback loop in `mcp_adk_agent_runner` to provide structured error analysis back to the model, rather than just raw stack traces.

### 4. MCP Server Launch

Improving code generation is an ongoing problem, but we want to get a MVP out the door to gather feedback and immediately help customers.

*   **Soft-launch MCP in late-January**
*   **Polish Tasks:**
    *   **Error Propagation:** Ensure that exceptions within the MCP server (e.g., `benchmarks/answer_generators/gemini_cli_docker/`) are correctly propagated to the client with distinct error codes (e.g., distinguishing between `FAIL_SETUP` and `FAIL_VALIDATION`).
    *   **Logging:** Add structured logging to the MCP server to trace tool execution paths for easier debugging.