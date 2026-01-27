# Contributing to Agent Generator

Welcome! This repository is a data-driven framework for generating and evaluating AI agents. This guide outlines the project's structure, development workflow, and standards to ensure consistency and quality.

## 1. Project Philosophy

*   **Agentic-First:** We prefer tools that can be run autonomously by agents.
*   **Data-Driven:** All benchmarks and evaluations are based on persistent data (YAML/JSON), not transient execution.
*   **Structured Output:** Code should prefer Pydantic models over unstructured dictionaries.
*   **Separation of Concerns:** Execution logic (`benchmarks/`) is strictly separated from Analysis logic (`tools/`) and Data (`ai/`).

## 2. Directory Structure

Understanding where files belong is critical.

| Directory | Purpose |
| :--- | :--- |
| **`ai/`** | **Central Context Hub.** Stores all AI inputs and outputs. <br> • `instructions/`: Input prompts, Knowledge Graph, Experiments. <br> • `reports/`: Generated analysis reports, Logs, and Doc caches. |
| **`benchmarks/`** | **Execution Engine.** The core testing framework. <br> • `answer_generators/`: Candidate agents (the "Systems Under Test"). <br> • `benchmark_definitions/`: Test cases (YAML) and ground truth. <br> • `runner/`: Execution environments (Docker/Podman wrappers). |
| **`scripts/`** | **Shell Helpers.** Bash scripts for orchestration and convenience. <br> • `benchmark_run.sh`: Main entry point for running benchmarks. |
| **`tools/`** | **Python Utilities.** Specialized sub-systems and libraries. <br> • `analysis/`: Forensic engines for analyzing run logs. <br> • `target_ranker/`: Static analysis for codebase mapping. <br> • `benchmark_generator/`: The agentic system for generating new tests. <br> • `debugging/`: Scripts for deep-diving into specific failures. |
| **`repos/`** | **Vendored Code.** External repositories (e.g., `adk-python`) used as targets for benchmark generation. |

## 3. Development Workflow

### Adding a New Tool
1.  **Category:** Identify the correct subdirectory in `tools/` (e.g., `tools/knowledge/` for indexing, `tools/debugging/` for forensics).
2.  **Structure:** If the tool is complex, create a new folder: `tools/my_tool/`.
3.  **Entry Point:** Provide a clean CLI entry point.
4.  **Tests:** Add unit tests in `tools/my_tool/tests/`.

### Adding a Benchmark Case
1.  Navigate to `benchmarks/benchmark_definitions/`.
2.  Choose the appropriate suite (e.g., `fix_errors`).
3.  Create a new case directory (e.g., `cases/my_new_case/`).
4.  Add `unfixed.py`, `fixed.py`, and `test_agent.py`.
5.  Register it in the suite's `benchmark.yaml`.

### Adding a Candidate Agent
1.  Navigate to `benchmarks/answer_generators/`.
2.  Create a new module (e.g., `experiment_99.py`).
3.  Implement a class inheriting from `AnswerGenerator`.
4.  Register it in `benchmarks/benchmark_candidates.py`.

## 4. Testing Strategy

We use `pytest` for all testing. Strict adherence to testing is required.

*   **Location:** Tests must reside in a `tests/` subdirectory relative to the code being tested.
    *   Example: `tools/target_ranker/ranker.py` -> `tools/target_ranker/tests/test_ranker.py`
*   **Core Framework:** General integration tests live in `benchmarks/tests/`.
*   **Naming:** Test files must start with `test_`.

### Running Tests
Run the full suite to ensure no regressions:
```bash
python -m pytest benchmarks/tests/ tools/
```

Run specific batches:
```bash
# Framework
python -m pytest benchmarks/tests/

# Generators
python -m pytest tools/benchmark_generator/tests/
```

## 5. Documentation Standards

### READMEs
**Every directory** (including sub-tools) must have a `README.md` containing:
1.  **Title & Purpose:** What does this component do?
2.  **Contents:** Brief list of key files.
3.  **Usage:** CLI commands or code snippets.
4.  **Testing:** Exact command to run the tests for this folder.

### Docstrings
All public functions and classes must have Python docstrings.

## 6. Code Style
*   **Type Hinting:** Use `typing` and `pydantic` heavily.
*   **Imports:** Use absolute imports (e.g., `from tools.utils import ...`) to avoid circular dependency issues.
*   **Async:** Prefer `async/await` for I/O bound operations (especially LLM calls).

## 7. Data Formats

*   **Mandatory YAML:** For configuration, static data, and intermediate artifacts, **always use YAML (`.yaml`)**.
*   **No JSON or JSONL:** JSON and JSON Lines (`.jsonl`) are strictly prohibited for stored data.
    *   **Rationale:** The Gemini CLI uses `ripgrep` for context retrieval. `ripgrep` returns entire lines when a keyword matches. Since JSON/JSONL can contain massive objects on a single line, a match can result in a giant, unreadable blob that pollutes the agent's context window and wastes tokens. YAML's multi-line structure ensures that `ripgrep` returns concise, relevant snippets.

