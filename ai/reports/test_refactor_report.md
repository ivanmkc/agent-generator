# Test Refactoring & Mocking Strategy Report

## 1. Mocking Philosophy & Strategy
**Goal:** Ensure tests are reliable, fast, and resistant to implementation drift while avoiding "mocking the implementation."

**Strategy:**
*   **Mock at Boundaries:** Mock external systems (Cloud APIs, Docker/Podman, HTTP requests). Do NOT mock internal methods of the class under test unless absolutely necessary (e.g., infinite loops, heavy compute).
*   **Use Real Objects for Data:** Prefer using real data models (Pydantic objects) over mocks for simple data structures to ensure schema compliance.
*   **Fixtures over Setup/Teardown:** Use `pytest` fixtures in `conftest.py` for shared resources (like `ApiKeyManager` mocks) to reduce boilerplate in test files.
*   **Isolation:** Unit tests must not require a running container or valid API keys. Integration tests should handle those.

## 2. Refactoring Opportunities

### A. Consolidate `ApiKeyManager` Mocks
*   **Problem:** Multiple test files (`test_answer_generators.py`, `test_gemini_cli_podman_answer_generator.py`) manually recreate `MagicMock(spec=ApiKeyManager)`.
*   **Solution:** Create a shared fixture `mock_api_key_manager` in `benchmarks/tests/unit/conftest.py` that provides a configured mock.
*   **Rationale:** Reduces code duplication and ensures all tests use a consistent mock interface that matches the current `ApiKeyManager` signature (async methods).

### B. Consolidate `PodmanContainer` Mocks
*   **Problem:** `test_gemini_cli_podman_answer_generator.py` patches `PodmanContainer` locally. If other tests use Podman logic, they will duplicate this.
*   **Solution:** Move the `mock_container` fixture to `benchmarks/tests/unit/conftest.py`.
*   **Rationale:** Centralizes the definition of a "healthy" container mock for reuse.

### C. Standardize File System Testing
*   **Problem:** `test_adk_tools.py` manually creates temp dirs in `setUp`.
*   **Solution:** Refactor to use pytest's `tmp_path` fixture which handles cleanup automatically and provides a `pathlib.Path` object directly.
*   **Rationale:** Modernizes the test suite to idiomatic pytest patterns.

### D. Folder Restructuring
*   **Suggestion:**
    *   Move `benchmarks/tests/integration/predefined_cases.py` to `benchmarks/tests/fixtures/cases.py` to verify it's treated as data/fixtures, not tests.
    *   Ensure `benchmarks/tests/unit/data/` contains all static test artifacts (like CLI output text files) to avoid scattering string literals in test code.

## 3. Implementation Plan
1.  Create `benchmarks/tests/unit/conftest.py` (if not exists) and populate with shared mocks.
2.  Refactor `test_answer_generators.py` and `test_gemini_cli_podman_answer_generator.py` to use these shared fixtures.
3.  Rewrite `test_adk_tools.py` to use `tmp_path`.
