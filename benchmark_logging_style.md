# Benchmark Logging Style Guide

This document describes the expected format, hierarchy, and color coding for the benchmark runner's console output. The logging is designed to be hierarchical, concise, and visually distinct for easy debugging and status tracking.

## 1. Hierarchy & Structure

The logging follows a strict nesting structure to reflect the execution flow:

1.  **Agent (Generator)**: The top-level block. Everything related to a specific agent's run is nested under this.
2.  **Benchmark Suite**: Implicitly grouped, but logs show loading of suites.
3.  **Benchmark Case**: A distinct block for each test case.
    *   **Attempts**: Individual generation attempts (retries) are nested within the case block.
    *   **Result**: The final pass/fail status and summary for the case.

## 2. Color Coding

The output uses standard ANSI colors (via `colorama`) to distinguish status and sections:

*   **CYAN (`Fore.CYAN`)**:
    *   Section Headers (e.g., `▶ Agent: ...`, `▶ Case: ...`).
    *   Informational summaries (e.g., "Total: 10, Passed: 8").
*   **GREEN (`Fore.GREEN`)**:
    *   Success status (`Attempt 1: Success`).
    *   Final Pass result (`Result: PASS ✔`).
*   **RED (`Fore.RED`)**:
    *   Failure status (`Attempt 1: Failed`).
    *   Errors (`Validation Error: ...`, `Generation Error: ...`).
    *   Final Fail result (`Result: FAIL ✘`).
*   **YELLOW (`Fore.YELLOW`)**:
    *   Warnings.
    *   Retry attempts (e.g., `Attempt 1: Failed - Timeout`).
*   **LIGHT BLACK / DIM (`Fore.LIGHTBLACK_EX`)**:
    *   Debug info or reproduction paths (e.g., `Reproduce: /tmp/...`).

## 3. Example Output

```text
▶ Agent: gemini-2.5-flash
  Setting up answer generator...
  Loading benchmark suite: benchmarks/benchmark_definitions/fix_errors/benchmark.yaml
  
  ▶ Case: fix_errors/simple_syntax_error
    Attempt 1: Success
    Result: PASS ✔

  ▶ Case: fix_errors/complex_logic
    Attempt 1: Failed - 500 Internal Error
    Attempt 2: Failed - Rate Limit
    Attempt 3: Success
    Validation Error: Output '5' does not match expected '42'
    Result: FAIL ✘
    Reproduce: /tmp/fix_errors_complex_logic_test.py

  ▶ Case: fix_errors/hard_crash
    Attempt 1: Failed - Timeout
    Attempt 2: Failed - Timeout
    Attempt 3: Failed - Timeout
    Validation Error: Generation failed after 3 attempts.
    Result: FAIL_GENERATION ✘

  ... (more cases) ...

  Completed all tasks for gemini-2.5-flash.
  Tearing down answer generator...

▶ Summary of Progress
  gemini-2.5-flash: 10 of 10 tasks completed.


SUMMARY TABLE
--------------------------------------------------
Benchmark                                          | Result     | Duration | Attempts
--------------------------------------------------
fix_errors/simple_syntax_error                     | PASS       |   1.20s | 1
fix_errors/complex_logic                           | FAIL       |   5.43s | 3
fix_errors/hard_crash                              | FAIL_GEN   |  15.00s | 3
...
--------------------------------------------------
Total: 10, Passed: 8, Failed: 2 (80.0%)
```

## 4. Key Behaviors

*   **Silent Retries**: Intermediate failures (retries) are logged succinctly within the case block ("Attempt X: Failed") rather than dumping full stack traces, keeping the output clean.
*   **Atomic Case Blocks**: All information for a specific case (attempts, errors, final result) is grouped together under the `▶ Case: ...` header.
*   **Final Summary**: A table is printed at the very end of the run (or agent run) to provide a quick "glanceable" report of all results.
