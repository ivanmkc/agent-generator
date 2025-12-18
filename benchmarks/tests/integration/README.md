# Integration Tests

This directory contains integration tests for the Answer Generators within the `benchmarks` suite. These tests verify the end-to-end functionality of different generator implementations (e.g., direct API, CLI, Podman, Cloud Run) against various benchmark case types (API understanding, multiple choice, fix error).

## Primary Test Suite

- [`test_unified_generators.py`](./test_unified_generators.py): This is the main, parameterized integration test suite that runs a comprehensive set of capabilities and execution tests across all configured `AnswerGenerator` types defined in [`conftest.py`](./conftest.py).
  - **Debugging Note:** This suite runs tests sequentially (or with low concurrency). If the high-concurrency benchmark orchestrator is failing due to infrastructure limits (e.g., Podman crashing), use this test to verify that the *logic* of the generators is correct in isolation.

## Specific Integration Tests

While `test_unified_generators.py` covers most cases, the following tests remain for specific purposes:

- [`test_benchmark_orchestrator_integration.py`](./test_benchmark_orchestrator_integration.py): **System-Level Verification.** Unlike the unified suite which tests individual components, this tests the `benchmark_orchestrator` pipeline itself. It verifies that the system can correctly load benchmark suites, dispatch jobs to generators, and aggregate results using a known-good baseline (`GroundTruthAnswerGenerator`).
- [`test_cloud_run_stability.py`](./test_cloud_run_stability.py): Dedicated to testing the stability and resilience of Cloud Run deployments under load.
- [`test_concurrency_limits.py`](./test_concurrency_limits.py): Verifies that concurrency limits are correctly applied and handled by the generators.
- [`test_baseline_generators.py`](./test_baseline_generators.py): Tests the functionality of baseline generators:
  - `GroundTruthAnswerGenerator`: Ensures benchmark integrity (must pass 100%).
  - `TrivialAnswerGenerator`: Ensures benchmarks aren't trivially solvable (must fail most).

## Configuration

Integration tests rely on fixtures defined in [`conftest.py`](./conftest.py) to set up and tear down `AnswerGenerator` instances, including configurations for local CLI, Podman, and Cloud Run environments. Some tests may be skipped if required environment variables (e.g., `GEMINI_API_KEY`, `GOOGLE_CLOUD_PROJECT`) or tools (`podman`) are not available.