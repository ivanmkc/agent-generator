# Benchmark Definitions

This directory contains the YAML files that define the benchmark suites for the ADK Benchmark Framework. Each YAML file represents a collection of benchmark cases that the framework can run.

## Structure

- **`api_understanding/`**: Contains benchmarks that test an AI's understanding of the ADK's public API. Each case consists of a question about the API, the expected code snippet as an answer, and metadata for validation.

- **`fix_errors/`**: Contains benchmarks that evaluate an AI's ability to fix broken code snippets. Each case points to a test file in the `fix_error` directory that is intentionally broken.

- **`diagnose_setup_errors_mc/`**: Multiple-choice benchmarks focusing on diagnosing setup and configuration errors.

- **`configure_adk_features_mc/`**: Multiple-choice benchmarks testing the configuration of various ADK features.

- **`predict_runtime_behavior_mc/`**: Multiple-choice benchmarks where the model must predict the runtime behavior of a given code snippet.

## Multiple Choice (MC) Context Isolation

For all MC benchmarks (ending in `_mc`), strict context isolation is enforced. Test files in these directories must use **snippet tags (`# --8<-- [start:...]` and `# --8<-- [end:...]`)** to wrap **only** the code snippet relevant to the question.

**Crucially:**
*   **Do not** use `# LLM_CONTEXT_BEGIN` or `# LLM_CONTEXT_END` in MC benchmark files; these are specific to `fix_errors` benchmarks.
*   **Do not** include the test function, assertions, or explanatory comments inside the snippet tags.
*   **Do** wrap the code snippet in a helper function (e.g., `code_under_test`) if necessary to make it a standalone block.

This ensures that the model answers based on its understanding of the code and the ADK, without being "fed" the answer from the test's validation logic.

## Usage

To run a benchmark suite, you provide the path to its YAML file to the `benchmark_orchestrator.run_benchmarks()` function (typically called from a script like `benchmark_debug.py` or `test_benchmarks.py`). The orchestrator will then parse the file and execute each benchmark case against the specified answer generators.

To add a new benchmark suite, create a new YAML file in this directory following the structure of the existing files.

## Verification Scripts

Each benchmark suite directory (e.g., `fix_errors/`) contains a `verify.py` script. These scripts are used to validate the integrity of the benchmark definitions, ensuring that:
1. The `benchmark.yaml` file is valid YAML.
2. All referenced test files exist.
3. Test files contain the required placeholders (e.g., `# BEGIN: CODE` and `# END: CODE`).

## Running Tests
To run the `fix_errors` tests directly, you can use the following command from the root of the project. **Crucially, you must use the `--import-mode=importlib` flag.**

```bash
python -m pytest ./benchmarks/benchmark_definitions/fix_errors/cases/ --import-mode=importlib
```

To run a verification script, execute it using the project's Python environment:

```bash
# Verify fix_errors benchmarks
env/bin/python benchmarks/tests/verification/test_verify_fix_errors.py

# Verify api_understanding benchmarks
env/bin/python benchmarks/benchmark_definitions/api_understanding/verify.py
```

Run these scripts after modifying or adding new benchmarks to ensure your definitions are correct before running the full test suite.
