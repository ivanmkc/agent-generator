# Codebase Knowledge MCP Server Tests

This directory contains the test suite for the `codebase-knowledge-mcp` package.

## Test Structure

### 1. Unit Tests (`test_*.py`)
These tests use `unittest.mock` to verify CLI command logic without running the actual server.

*   **`test_manage_mcp.py`**:
    *   Verifies configuration parsing (JSON vs CSV).
    *   Tests the `setup` command flow (merging configs, interactive prompts).
    *   Tests utility functions like `ask_confirm`.

*   **`test_remove_command.py`**:
    *   Verifies the `remove` command behavior.
    *   scenarios: Interactive mode, Quiet mode (`--quiet`), and Force mode (`--force`).

*   **`test_debug_command.py`**:
    *   Verifies the `debug` command's self-diagnosis logic.
    *   Ensures accurate success/failure reporting by mocking MCP client responses.
    *   Covers edge cases like benign "Error" text in docstrings vs. real protocol errors (`isError=True`).

### 2. Integration Tests
These tests validate interactions between components or against a real server instance.

*   **`test_debug_edge_cases.py`**:
    *   **Integration-like**: Runs the `debug` command against a locally spawned server process.
    *   Uses a "poisoned" `ranked_targets.yaml` to verify robustness against data that mimics error messages.

*   **`test_tools_e2e.py`**:
    *   **End-to-End**: Connects a real MCP client to a real server subprocess.
    *   Verifies actual tool execution (`list_modules`, `inspect_symbol`) using a custom test index.
    *   Ensures the server returns correct content and error messages.

*   **`test_integration.py`** (Legacy/Internal):
    *   Tests internal server modules (`server.py`, `index.py`) by mocking the `mcp` library wrapper.
    *   Verifies symbol lookup logic and source reading.

## Running Tests

Run the full suite using `pytest`:

```bash
# Run all tests
python -m pytest tools/adk_knowledge_ext/tests/

# Run specific test file
python -m pytest tools/adk_knowledge_ext/tests/test_tools_e2e.py

# Run with verbose output
python -m pytest -v tools/adk_knowledge_ext/tests/
```

## Adding New Tests

*   **For CLI Commands:** Add to `test_<command>_command.py`. Use mocks for server interaction.
*   **For Tool Logic:** Add to `test_tools_e2e.py`. Create a custom `ranked_targets.yaml` fixture if needed.
*   **For Server Internals:** Add to `test_integration.py` if testing internal functions directly.
