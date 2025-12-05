# Fix Errors Benchmark

This benchmark evaluates an LLM's ability to fix broken or incomplete ADK agent implementations.

## Structure

The benchmark uses a directory-based structure for test cases. All cases are located in the `cases/` directory.

Each test case consists of a dedicated subdirectory (e.g., `cases/01_my_case/`) containing three essential files:

1.  **`unfixed.py`**: A Python file containing the broken or incomplete code. This is what the LLM reads and is asked to fix.
2.  **`fixed.py`**: A Python file containing the correct, working implementation. This serves as the ground truth.
3.  **`test_agent.py`**: A standard `pytest` file that imports the generated solution (or the fixed/unfixed code during testing) and runs assertions to verify its correctness.

An entry in `benchmark.yaml` points to this directory and defines the problem description and requirements.

## Running the Benchmarks

To run the benchmarks and verify the test cases, use `pytest` from the project root. **Crucially, you must use the `--import-mode=importlib` flag.** This flag ensures that Python's import system correctly handles the non-unique module names (`fixed.py`, `unfixed.py`) present in each test case directory by treating them as distinct modules based on their file path.

```bash
# Run all fix_errors benchmarks
python -m pytest benchmarks/benchmark_definitions/fix_errors/ --import-mode=importlib

# Run a specific test case
python -m pytest benchmarks/benchmark_definitions/fix_errors/cases/01_single_llm_agent/test_agent.py --import-mode=importlib
```

## Standards for Creating `fix_error` Test Cases

To ensure consistency and focus the LLM on the relevant task, all `fix_error` test cases **must** adhere to the following:

1.  **Model Output**: The LLM is expected to provide the complete and correct Python solution code. This code typically replaces the content of `unfixed.py`.

2.  **`create_agent` Function Signature**: The generated Python file (and thus `fixed.py` and `unfixed.py`) **must** contain a function with the exact signature `def create_agent(model_name: str) -> BaseAgent:`. The `test_agent.py` will import and call this function.

3.  **Exclude Test Boilerplate**: The solution provided by the LLM should *only* contain the agent definition and necessary imports/helpers. It should **not** include:
    *   Imports from `__future__`.
    *   Imports from `pytest`.
    *   Imports from `benchmarks.test_helpers`.
    *   `pytestmark` definitions.
    *   Test functions (e.g., `async def test_my_feature(): ...`).
    *   Helper functions for running tests (e.g., `run_test()`, `assert_test()`)

By following these standards, we ensure that the LLM is only presented with the information it needs to solve the agent construction problem, free from the surrounding test infrastructure.

### **Checklist for Designing `fix_error` Cases**

#### **What is Expected**

1.  **Directory Structure:**
    *   Create a new directory in `benchmarks/benchmark_definitions/fix_errors/cases/` (e.g., `26_new_error_case`).
    *   The directory MUST contain three files: `unfixed.py`, `fixed.py`, and `test_agent.py`.
    *   **Do NOT include `__init__.py` files** in the case subdirectories. This prevents package name collisions and ensures the `importlib` import mode works as expected.

2.  **`unfixed.py` (The Problem):**
    *   Define a function `create_agent(model_name: str) -> BaseAgent`.
    *   The function MUST raise an error (e.g., `NotImplementedError`, `ImportError`, `ValueError`) OR return an agent with a flaw (syntax error, logic bug, incorrect configuration).
    *   Include a docstring for `create_agent` with:
        *   **Instructions:** Clear, step-by-step goals for the agent to achieve (this is the prompt for the LLM).
        *   **Args:** `model_name`.
        *   **Returns:** Description of the expected agent.

3.  **`fixed.py` (The Solution):**
    *   Define the same function `create_agent(model_name: str) -> BaseAgent`.
    *   Provide a complete, working implementation that satisfies the instructions in `unfixed.py`.
    *   Ensure strict adherence to ADK patterns (e.g., correct imports, correct class usage).
    *   The agent returned MUST pass all verification steps defined in `test_agent.py`.

4.  **`test_agent.py` (The Verification):**
    *   **Imports:** Use `import unfixed` and `import fixed` locally within test functions to avoid top-level import errors or circular dependencies.
    *   **Test Case 1 (`test_create_agent_unfixed_fails`):**
        *   Import `unfixed`.
        *   **Must actively verify failure.** Use `pytest.raises(...)` for exceptions, or asserts that check for *incorrect* values/state (e.g. `assert agent.instruction != "correct instruction"`). Do not just run the code and assert `True` or `is not None` unless `None` is the failure mode.
    *   **Test Case 2 (`test_create_agent_passes`):**
        *   Import `fixed`.
        *   Call `root_agent = fixed.create_agent(MODEL_NAME)`.
        *   **Run Agent:** Use `await run_agent_test(root_agent, ...)` to simulate an interaction.
        *   **Verify Output:** Assert that the response contains expected keywords/values.
        *   **Verify Structure:** Assert that the agent's properties (name, tools, sub-agents, config) are correctly set. **This is critical.** Don't just check the text output; check the *code structure* (e.g., `assert root_agent.name == "expected_name"`, `assert len(root_agent.tools) == 1`).

5.  **Agent Logic:**
    *   The agent must be an instance of `BaseAgent` (usually `LlmAgent`, `SequentialAgent`, `LoopAgent`, etc.).
    *   Use `model_name` passed to the function.

#### **What is Restricted (Do Not Do)**

1.  **Do NOT modify `sys.path` in `test_agent.py`:**
    *   Avoid `sys.path.append(...)`. The test runner handles discovery.

2.  **Do NOT use top-level imports for the case modules in `test_agent.py`:**
    *   Do NOT write `import unfixed` at the top of the file.
    *   ALWAYS import inside the test functions (`def test_...(): import unfixed`). This prevents cross-contamination between test cases.

3.  **Do NOT rely solely on LLM text output for verification:**
    *   Text output is non-deterministic. Always include structural assertions (checking object attributes, types, configuration values) to ensure the *code* is correct, not just that the LLM guessed the right answer.

4.  **Do NOT assume external dependencies:**
    *   Only use libraries available in the standard ADK environment.

5.  **Do NOT leave `unfixed.py` empty or trivial:**
    *   It must represent a plausible starting state (e.g., a template with `raise NotImplementedError` or code with a specific bug).

6.  **Do NOT hardcode model names:**
    *   Always use the `model_name` argument passed to `create_agent`.
