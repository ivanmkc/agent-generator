# Answer Generators

This directory contains the implementations of various "Answer Generators" used in the ADK Benchmark Framework. An Answer Generator is responsible for producing an answer (typically code) for a given benchmark case.

## Structure

*   **`base.py`**: Defines the abstract `AnswerGenerator` base class.
*   **`llm_base.py`**: Base class for generators that use Large Language Models, handling prompt loading and context.
*   **`ground_truth_answer_generator.py`**: Returns the "fixed" code from the benchmark definition (perfect score reference).
*   **`trivial_answer_generator.py`**: Returns empty or simple answers (sanity check/baseline).
*   **`gemini_answer_generator.py`**: Uses the Gemini Python SDK to generate answers.
*   **`gemini_cli_answer_generator.py`**: Uses the Gemini CLI tool to generate answers.
*   **`adk_answer_generator.py`**: Uses ADK agents to generate answers. Supports `StructuredWorkflowAdk` for complex tasks involving planning, coding, and verification loops.
*   **`adk_agents.py`**: Defines specific ADK agent configurations, including the `StructuredWorkflowAdk` sequential agent (Setup -> Knowledge Retrieval -> Planner -> Implementation Loop -> Final Output). **See [ADK_AGENTS.md](ADK_AGENTS.md) for detailed architecture documentation.**
*   **`adk_schemas.py`**: Pydantic models defining the structured output for each step of the ADK workflow (`Plan`, `VerificationPlan`, `SetupContext`, etc.).
*   **`adk_tools.py`**: Custom tools for ADK agents, including file system operations, shell commands, and `get_module_help` for efficient API discovery.
*   **`gemini_cli_docker/`**: Contains the Docker-based Gemini CLI generator and its sandbox resources.
*   **`prompts/`**: Contains prompt templates used by the LLM-based generators.

## Adding a New Generator

To add a new generator:
1.  Inherit from `AnswerGenerator` (or `LlmAnswerGenerator`).
2.  Implement `generate_answer`.
3.  Register it in `benchmarks/benchmark_candidates.py`.
