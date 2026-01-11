# Call Graph Analysis: Benchmark vs. Integration Test Workflows

This document compares the architectural call graphs and execution models of two distinct workflows within the `agent-generator` project: the comprehensive benchmark suite initiated by `notebooks/run_benchmark_notebook.sh` and the optimized integration test run orchestrated by `benchmarks/tests/integration/test_unified_generators.py`.

## 1. Call Graph: Benchmark Suite Workflow (`notebooks/run_benchmark_notebook.sh`)

This workflow is designed for extensive evaluation of various answer generators against a broad set of benchmark definitions, focusing on performance, accuracy, and error analysis.

**High-Level Flow:**
```mermaid
graph TD
    A[run_benchmark_notebook.sh (Bash)] --> B{Papermill Execution}
    B --> C[benchmark_run.template.ipynb (Python Notebook)]
    C --> D[benchmark_run.template.py:run_comparison()]
    D -- Iterates Generators --> E{Generator Instance (e.g., GeminiCliPodmanAnswerGenerator)}
    E --> F[Generator.setup()]
    F --> G[benchmark_orchestrator.py:run_benchmarks()]
    G -- Asynchronously (max_concurrency=40) --> H[benchmark_orchestrator.py:_run_single_benchmark()]
    H --> I[Generator.generate_answer()]
    I --> J[Result & Trace Logging]
    E --> K[Generator.teardown()]
    C --> L[Result Processing & Reporting (Pandas, Markdown)]
```

**Description:**
1.  **`run_benchmark_notebook.sh`**: A shell script that serves as the entry point. It sets up an output directory, converts a Python script to a Jupyter notebook, and then executes it using `papermill`.
2.  **`benchmark_run.template.py` (via `papermill`)**: This Python script, executed as a notebook, orchestrates the entire benchmark process.
    *   It defines a list of `CANDIDATE_GENERATORS` (e.g., `GeminiCliPodmanAnswerGenerator(image_name="gemini-cli:base")` as seen in `benchmarks/benchmark_candidates.py`).
    *   The `run_comparison` function iterates through each generator sequentially.
    *   For each generator, `generator.setup()` is called once to initialize resources (e.g., build a Podman image and start its API server container).
    *   It then calls `benchmark_orchestrator.run_benchmarks()`.
3.  **`benchmark_orchestrator.py:run_benchmarks()`**: This function is responsible for running all defined benchmark cases (loaded from YAML files) against the currently active generator.
    *   It uses `asyncio.Semaphore` to manage concurrency, allowing up to `PODMAN_CONFIG.MAX_GLOBAL_CONCURRENCY` (currently 40) benchmark cases to run in parallel *for that single generator instance*.
    *   Each benchmark case involves calling `generator.generate_answer()`.
4.  **Reporting**: After all benchmarks for a generator are complete, the results are processed, summarized, and detailed Markdown reports are generated.
5.  **Teardown**: Finally, `generator.teardown()` is called to release resources (e.g., stop the Podman container).

## 2. Call Graph: Integration Test Workflow (`benchmarks/tests/integration/test_unified_generators.py`)

This workflow focuses on verifying the functional correctness and integration of specific generator implementations using the `pytest` framework, with an emphasis on optimized resource usage.

**High-Level Flow:**
```mermaid
graph TD
    A[test_unified_generators.py:run_orchestrator() (Python)] --> B{Generator Configuration List}
    B -- Iterates Sequentially --> C{Generator Instance (e.g., GeminiCliPodmanAnswerGenerator)}
    C --> D[Generator.setup() (Starts Podman Container/Service)]
    D --> E[asyncio.create_subprocess_exec("pytest -n auto -k gen_id ...")]
    E -- Spawns Pytest Process --> F{Pytest Master Process}
    F -- Distributes to Pytest-xdist Workers --> G[Pytest Worker Process (e.g., Worker 1)]
    G --> H[benchmarks/tests/integration/conftest.py:podman_base_test_case() (Fixture)]
    H -- Detects TEST_GENERATOR_URL --> I[Generator Instance (Proxy Mode)]
    I --> J[test_generator_capabilities()]
    I --> K[test_generator_execution()]
    I --> L[test_generator_memory_context()]
    J & K & L --> M[Generator.run_cli_command() / generate_answer() (via HTTP to existing container)]
    C --> N[Generator.teardown() (Stops Podman Container)]
```

**Description:**
1.  **`test_unified_generators.py:run_orchestrator()`**: The main entry point in this script. It defines specific generator configurations (e.g., `podman_base_test_case`).
2.  **Sequential Generator Setup**: The orchestrator iterates through these configurations. For each, it instantiates a `GeminiCliPodmanAnswerGenerator` and calls `generator.setup()`. **Crucially, this is where the actual Podman container is built and started, and its service URL is obtained.**
3.  **`pytest` Subprocess Execution**: Instead of directly running tests, the orchestrator spawns a `pytest` subprocess with arguments like `-n auto` (for `pytest-xdist` parallelism) and `-k <generator_id>` (to filter tests for the current generator). It passes the service URL via environment variables (`TEST_GENERATOR_URL`).
4.  **`conftest.py` Fixture (Proxy Pattern - The "Optimized Run" Core)**:
    *   Within the `pytest` worker processes, fixtures like `podman_base_test_case` in `conftest.py` are executed.
    *   This fixture checks for the `TEST_GENERATOR_URL` environment variable. If present, it creates the `GeminiCliPodmanAnswerGenerator` in a "proxy mode", where it connects to the already running container specified by the URL, rather than attempting to build and start a new one.
    *   This avoids redundant container setups within each parallel `pytest-xdist` worker.
5.  **Test Execution**: The `pytest` workers then run the actual test functions (`test_generator_capabilities`, `test_generator_execution`, `test_generator_memory_context`), which interact with the generator instance (now effectively a client to the orchestrator's server). These tests run in parallel across the `pytest-xdist` workers.
6.  **Teardown**: After the `pytest` subprocess completes for a given generator, the orchestrator calls `generator.teardown()` to stop the container.

## 3. Key Architectural Differences

| Feature               | Benchmark Suite Workflow (`run_benchmark_notebook.sh`)                               | Integration Test Workflow (`test_unified_generators.py`)                                             |
| :-------------------- | :----------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------- |
| **Primary Purpose**   | Quantitative performance & accuracy measurement across many scenarios.               | Functional correctness, API integration, and behavioral validation of generators.                     |
| **Entry Point**       | Bash script orchestrating `papermill`.                                               | Python script orchestrating `pytest` subprocesses.                                                    |
| **Orchestration**     | Python script (`benchmark_run.template.py`) executing within `papermill`.            | Python script launching and managing `pytest` as a child process.                                     |
| **Test Data Source**  | YAML-defined benchmark cases (`benchmarks/benchmark_definitions/`).                  | Hardcoded `GeneratorTestCase` objects defined in Python (`conftest.py` and `predefined_cases.py`).  |
| **Concurrency Model** | `asyncio.Semaphore` (within a single process) for parallel benchmark case execution (max 40). | `pytest-xdist` (multi-processing) for parallel execution of test functions (e.g., 3 tests per generator across CPU cores). |
| **Resource Setup**    | `generator.setup()` called once per generator in the orchestrator's process.         | `generator.setup()` called once in the orchestrator's process, *then* `pytest` workers connect as clients via a proxy pattern. |
| **Optimization**      | Efficient use of `asyncio` for many concurrent *requests* against one setup generator. | "Optimized Run" by using a single, long-lived container for all tests of a generator, avoiding redundant container spins for each `pytest-xdist` worker. |
| **Output / Reporting**| Rich DataFrame analysis, detailed Markdown reports, latency/cost metrics.            | Standard `pytest` output (pass/fail), with detailed assertion messages.                              |

## 4. Detailed Explanation of "Optimized Run" in Integration Tests

The term "optimized run" in the context of `test_unified_generators.py` refers to a specific strategy for efficiently running resource-intensive tests, particularly those involving containerized environments like Podman.

**The Problem**:
When running tests with `pytest-xdist` (enabled by `-n auto`), `pytest` can spawn multiple worker processes to execute tests in parallel. If each worker were to independently set up a Podman container, it would lead to:
1.  **High Resource Consumption**: Multiple Podman containers (each potentially a full CLI server) running concurrently, consuming significant CPU, RAM, and potentially conflicting on ports.
2.  **Slow Execution**: Each worker would incur the overhead of building and starting its own container.
3.  **Flakiness**: Race conditions or resource exhaustion could lead to unreliable test results.

**The Optimization (Proxy Pattern)**:
`test_unified_generators.py` addresses this by employing a "proxy pattern" to manage the container lifecycle:

1.  **Centralized Container Management**: The `run_orchestrator()` function in `test_unified_generators.py` takes on the responsibility of starting and stopping the `Podman` container (via `generator.setup()` and `generator.teardown()`) *once* per generator configuration.
2.  **Service URL Exposure**: After the container is successfully started, the orchestrator retrieves its service URL (e.g., `http://localhost:port`) and passes this URL to the `pytest` subprocess via an environment variable (`TEST_GENERATOR_URL`).
3.  **Fixture-Based Proxy**: The `conftest.py` file, which defines fixtures for `pytest`, contains logic to detect this environment variable.
    *   When a `pytest-xdist` worker process requests a `GeneratorTestCase` fixture (e.g., `podman_base_test_case`), the fixture checks if `TEST_GENERATOR_URL` is set.
    *   If it is, instead of building and running a new Podman container, the fixture creates a `GeminiCliPodmanAnswerGenerator` instance in a "proxy mode" by passing the `service_url` to its constructor. In this mode, the generator acts as a client, making HTTP requests to the already running container managed by the orchestrator process.
    *   If `TEST_GENERATOR_URL` is *not* set (e.g., if `pytest -n auto` is run directly without the orchestrator), the fixture `pytest.skip`s these resource-heavy tests to prevent the problems described above.

**Benefits of the Optimized Run**:
*   **Reduced Resource Usage**: Only one Podman container runs at a time for each generator's test suite, regardless of how many `pytest-xdist` workers are active.
*   **Faster Execution**: The overhead of container setup and teardown is amortized across all tests for a given generator.
*   **Increased Stability**: Avoids resource conflicts and flakiness associated with multiple independent container instances.
*   **Leverages `pytest-xdist` Effectively**: Allows the use of `pytest-xdist` for parallelizing individual test functions *against* a shared, stable backend service.
