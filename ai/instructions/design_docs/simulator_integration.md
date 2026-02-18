# Design Doc: Simulator Integration into Benchmark Framework

## Objective
Integrate the existing `tools/simulator` (a headless CLI simulation harness) into the `benchmarks` framework. This will allow us to run multi-turn, interactive CLI scenarios as standard benchmarks.

## Overview
We need to bridge two systems:
1.  **`tools/simulator`**: A standalone set of scripts that runs CLI simulations.
2.  **`benchmarks`**: Our main evaluation framework that runs cases and measures performance.

We will create a new Benchmark Case type (`SimulatorBenchmarkCase`) and a corresponding Answer Generator (`SimulatorAnswerGenerator`) that runs the simulation and reports the result.

## Important: Testing Strategy for Simulator Infrastructure

**CRITICAL NOTE FOR IMPLEMENTERS:**

When writing tests for the **simulator infrastructure itself** (e.g., tests in `tools/simulator/tests` or new tests for `SimulatorAnswerGenerator`), the goal is to verify that the **harness works**, not that the **Gemini CLI agent is perfect**.

The simulator runs a "Case" which includes:
-   **Reactors**: Determine how the simulated user responds.
-   **Verification**: Checks if the agent created the right files (`expected_files`) or passed a custom check (`custom_verify`).

**Infrastructure Tests Must Not Flake on Agent Behavior:**
-   **PASS**: The simulator successfully starts the CLI, sends prompts, receives responses, and *attempts* verification.
-   **PASS**: The simulator correctly reports `success=False` if the agent fails to create a file.
-   **FAIL**: The simulator crashes, hangs, throws an unhandled exception, or fails to launch the process.

**Do NOT assert `result.success is True` in infrastructure tests unless the case is trivial and deterministic (e.g., "echo hello").**
For complex cases, assert that `result.transcript` is populated and `result.success` is a boolean. We want to test the *runner*, not the *agent*.

To be clear, these verification steps (defined in `InteractiveSimulationCase`) **need NOT pass** for the infrastructure test to be considered "Green":
-   `expected_files: List[FileExpectation]`
-   `custom_verify: Optional[Callable[[str, Any], bool]]`

---

## Implementation Steps (Junior Engineer Guide)

### 1. Update Data Models (`benchmarks/data_models.py`)

**Goal:** Register the new "Simulator" type so the framework knows how to handle it.

*   Add `SIMULATOR = "simulator"` to the `BenchmarkType` enum.
*   Add `SimulatorAnswerOutput` (inheriting from `BaseAnswerOutput`). It should have `transcript: Any` and `is_correct: bool`.
*   Add `SimulatorBenchmarkCase` (inheriting from `BaseBenchmarkCase`). It should have `simulation_case: Any` (which will hold the `InteractiveSimulationCase`).
*   Update the `BenchmarkCase` and `AnswerOutput` `Annotated[Union[...]]` blocks at the bottom of the file to include these new classes.

### 2. Implement the Runner (`benchmarks/benchmark_runner.py`)

**Goal:** Define how to "verify" a simulator result.

*   Create `SimulatorRunner(BenchmarkRunner[SimulatorBenchmarkCase])`.
*   Implement `run_benchmark`. Use `self.ensure_valid_output(generated_answer, SimulatorAnswerOutput)`.
*   If `output.is_correct` is True, return `BenchmarkResultType.PASS`. Otherwise, return `BenchmarkResultType.FAIL_VALIDATION`.

### 3. Refactor Simulator to Async & Pexpect (`tools/simulator/runner.py`)

**Goal:** Make the simulator natively async and switch to `pexpect` for true interactive simulation.

*   **Switch to Pexpect:** The current implementation uses `subprocess.run` with headless flags (`-p`, `-r`). This is brittle and CLI-specific.
    *   **Why Pexpect?**
        1.  **True Interactivity:** It allocates a PTY (pseudo-terminal), forcing the CLI to believe it is running in a real terminal. This exercises the exact code paths (Ink UI, keypress handling, spinner rendering) that real users experience, catching bugs that headless modes miss.
        2.  **State Persistence:** We spawn the process *once* and interact with it over multiple turns. This is far more efficient and realistic than restarting the process with `-r/--resume` flags for every turn, which is slow and risks state serialization bugs.
        3.  **Universal Backend Support:** `pexpect` works with *any* interactive CLI (Claude, generic Python scripts, Bash), not just ones that implement a specific headless protocol like `gemini-cli`'s `-p` flag.
    *   **Refactoring Plan:**
        *   Refactor `SimulationRunner` to use `pexpect`.
        *   Use `asyncio.create_subprocess_exec` is an alternative if we only needed streams, but for PTY interaction, wrapping blocking `pexpect` calls in `loop.run_in_executor` is acceptable and robust.
*   **Async Wrapper:** Since `pexpect` is blocking, wrap the interaction loop in a thread using `loop.run_in_executor` inside the `run_async` method.
*   **API Key Manager:** Integrate `ApiKeyManager` to handle retries and key rotation for the LLM User Simulant.

### 4. Create the Answer Generator (`benchmarks/answer_generators/simulator_answer_generator.py`)

**Goal:** The bridge that calls the simulator.

*   Create `SimulatorAnswerGenerator(AnswerGenerator)`.
*   In `generate_answer`, call the simulator runner.
*   **Path Hack:** You MUST add `tools/simulator` to `sys.path` at the top of this file to allow importing from the `tools` folder.

---

## Task: Robust Retry Logic & ApiKeyManager Integration

**Problem:**
Currently, `LLMReactor` (which uses an LLM to decide the next user action) appears to fail immediately upon an API error (e.g., 429 Resource Exhausted) or has simple retry logic that doesn't rotate keys. This makes long-running benchmarks flaky.

**Requirement:**
The simulator must be robust against API failures. It should seamlessly integrate with the `core.api_key_manager.ApiKeyManager` to handle key rotation and retries, mirroring the behavior of `run_benchmarks.py`.

**Implementation Plan:**

1.  **Inject ApiKeyManager:**
    -   Update `SimulationRunner.run_async` (and `run`) to accept an optional `api_key_manager: ApiKeyManager` instance.
    -   Pass this manager down to `LLMUserSimulant` and `LLMReactor`.

2.  **Update LLM Call Sites:**
    -   Identify where `genai.Client` or `generate_content` is called (in `LLMUserSimulant.generate_reply` and `LLMReactor` evaluation loop).
    -   Wrap these calls in a retry loop that uses `ApiKeyManager`.

    *Draft Logic (Conceptual):*
    ```python
    # In tools/simulator/runner.py or a helper

    async def generate_with_retry(prompt, model, api_key_manager):
        # If no manager, fall back to single key from env
        if not api_key_manager:
             return await direct_call(prompt, model)
        
        # Use the manager's context manager which handles rotation on error
        async with api_key_manager.get_client(model) as client:
             return await client.generate_content_async(prompt)
    ```

3.  **Handle Quota Exhaustion:**
    -   If an API call fails with `429` (Resource Exhausted), the `ApiKeyManager` should automatically mark the current key as exhausted/rate-limited and provide a fresh key for the retry.
    -   The simulator should NOT crash; it should log a warning ("Key exhausted, rotating...") and continue the turn.

4.  **Verification:**
    -   Create a test case where the "first" key is a mock that always returns 429.
    -   Ensure the simulator successfully rotates to a "second" valid key and completes the simulation.

---

## Integration and Verification

To ensure your changes work with the existing unified test suite and the CLI, follow these steps:

### 1. Register a Test Case in `benchmarks/tests/integration/test_config.py`

This is where all generators are configured for the integration test suite (`test_unified_generators.py`).

1.  **Define a Config Model** in `benchmarks/tests/integration/config_models.py`:
    ```python
    class SimulatorGeneratorConfig(GeneratorConfig):
        type: Literal["simulator"] = "simulator"
        backend: str = "gemini-cli"
        
        def create_generator(self, model_name: str, project_id: str, api_key_manager: ApiKeyManager) -> AnswerGenerator:
            from benchmarks.answer_generators.simulator_answer_generator import SimulatorAnswerGenerator
            return SimulatorAnswerGenerator(backend=self.backend)
    ```
2.  **Add a Predefined Case** in `benchmarks/tests/integration/predefined_cases.py`:
    ```python
    from tools.simulator.models import InteractiveSimulationCase, ReactorAction, ActionType
    # (Ensure sys.path is handled in predefined_cases.py or imports are safe)
    
    TRIVIAL_SIM_CASE = SimulatorBenchmarkCase(
        id="test:trivial_sim",
        simulation_case=InteractiveSimulationCase(
            name="Trivial Integration Test",
            initial_prompt="echo 'HELLO'",
            max_turns=1,
            default_action=ReactorAction(type=ActionType.END_TEST, payload="Done")
        )
    )
    ```
3.  **Add to `GENERATOR_METADATA`** in `benchmarks/tests/integration/test_config.py`:
    ```python
    "simulator_test_case": SimulatorGeneratorConfig(
        id="simulator_test_case",
        custom_case=TRIVIAL_SIM_CASE
    )
    ```

### 2. Run the Unified Integration Test

Execute the standard test suite. It will now automatically pick up your new generator and run the trivial case.

```bash
pytest benchmarks/tests/integration/test_unified_generators.py -k simulator_test_case
```

**What to expect:**
-   `test_generator_execution` will call your generator.
-   The generator will run the trivial "echo HELLO" simulation.
-   The test will pass if the simulator doesn't crash and returns a valid transcript.

### 3. Run a Real Suite via CLI

Verify that the `run_benchmarks` CLI tool works with the new generator.

```bash
python -m benchmarks.cli.run_benchmarks --suite debug_suite --generator simulator-gemini-cli
```
*(Note: You will need to create a YAML suite file that defines a Simulator case or use a mock suite)*.