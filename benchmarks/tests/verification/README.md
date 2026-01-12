# Verification Scripts for ADK Benchmarks

This directory contains Python scripts dedicated to verifying the correctness and integrity of the ADK benchmark definitions found in `benchmarks/benchmark_definitions/`.

## Purpose

These scripts serve as a crucial regression testing mechanism. They validate that:

-   **API Surface Integrity**: Classes, methods, and functions referenced in benchmark questions (e.g., in multiple-choice options or explanations) continue to exist in the ADK codebase.
-   **Behavioral Consistency**: Core behaviors and configurations described in the benchmarks (e.g., `RunConfig` parameters, `App` initialization, plugin functionality) remain consistent with the library's implementation.
-   **Definition Accuracy**: The assumptions made by the benchmarks about the ADK API are still valid, helping to flag potential issues when the ADK library evolves.

## Usage

To run the verification script for the `advanced_adk_usage_benchmarks.yaml`:

```bash
python benchmarks/tests/verification/verify_advanced_benchmarks.py
```

Each verification script should be executed periodically, especially after significant changes to the ADK library, to ensure the benchmarks accurately reflect the current state of the codebase.

## Infrastructure Verification

This directory also contains scripts to verify the benchmark runner infrastructure itself:

-   **`verify_adk_runner.py`**: A smoke test for the ADK runner infrastructure, particularly for verifying MCP server functionality and containerized execution.
    ```bash
    python benchmarks/tests/verification/verify_adk_runner.py
    ```

-   **`verify_context7.py`**: Verifies the specific `context7` MCP tool functionality within the podman-based execution environment.
    ```bash
    python benchmarks/tests/verification/verify_context7.py
    ```

## Adding New Verification Scripts

When a new benchmark suite (`.yaml` file) is added, a corresponding verification script should be created in this directory. This script should:

1.  Import relevant ADK classes and modules.
2.  Implement `test_` prefixed functions to assert the existence of attributes, correctness of signatures, or expected behaviors. 
3.  Be runnable directly using `python <script_name>.py`.
4.  Be referenced in the header comments of its corresponding `.yaml` benchmark file.
