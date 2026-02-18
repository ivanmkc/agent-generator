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

---

## Implementation Steps

### Step 1: Update Data Models (`benchmarks/data_models.py`)

We need to define the data structures for our new benchmark type.

**1. Add `SIMULATOR` to `BenchmarkType` Enum:**

```python
class BenchmarkType(str, enum.Enum):
    # ... existing types ...
    SIMULATOR = "simulator"
```

**2. Define `SimulatorBenchmarkCase`:**
This class wraps the existing `InteractiveSimulationCase` from the simulator tools.

*Note: Since `tools/simulator` is not a proper package, we use `Any` for the `simulation_case` field to avoid complex import issues at the module level.*

```python
class SimulatorBenchmarkCase(BaseBenchmarkCase):
    """Represents a single simulator benchmark case."""
    
    benchmark_type: Literal[BenchmarkType.SIMULATOR] = BenchmarkType.SIMULATOR
    
    # We use Any here to avoid direct dependency on tools.simulator at module level
    simulation_case: Any = Field(..., description="The InteractiveSimulationCase object.")

    @property
    def runner(self) -> "SimulatorRunner":
        # Deferred import to avoid circular dependencies
        from benchmarks.benchmark_runner import SimulatorRunner
        return SimulatorRunner()

    def validate_answer_format(self, output: "AnswerOutput") -> None:
         if not isinstance(output, SimulatorAnswerOutput):
            raise AssertionError(f"Expected SimulatorAnswerOutput, got {type(output)}")

    def get_ground_truth(self) -> Optional[str]:
        return None

    def get_unfixed_code(self) -> Optional[str]:
        return None
```

**3. Define `SimulatorAnswerOutput`:**
This structure holds the result of the simulation.

```python
class SimulatorAnswerOutput(BaseAnswerOutput):
    """The expected output structure for a simulator benchmark."""
    
    benchmark_type: Literal[BenchmarkType.SIMULATOR] = BenchmarkType.SIMULATOR
    
    transcript: Any = Field(..., description="The simulation transcript (JSON-serializable dict).")
    is_correct: bool = Field(..., description="Whether the simulation was successful.")
```

**4. Update Unions:**
Add the new classes to `BenchmarkCase` and `AnswerOutput` unions.

```python
BenchmarkCase = Annotated[
    Union[
        FixErrorBenchmarkCase,
        ApiUnderstandingBenchmarkCase,
        MultipleChoiceBenchmarkCase,
        SimulatorBenchmarkCase, # <--- Added
    ],
    Field(discriminator="benchmark_type"),
]

AnswerOutput = Annotated[
    Union[
        FixErrorAnswerOutput,
        ApiUnderstandingAnswerOutput,
        MultipleChoiceAnswerOutput,
        SimulatorAnswerOutput, # <--- Added
    ],
    Field(discriminator="benchmark_type"),
]
```

### Step 2: Implement the Runner (`benchmarks/benchmark_runner.py`)

The runner is responsible for validating the output. For simulations, validation is simple: check the `is_correct` flag returned by the simulator.

**1. Import Models:**
Update imports to include `SimulatorBenchmarkCase` and `SimulatorAnswerOutput`.

**2. Create `SimulatorRunner` Class:**

```python
class SimulatorRunner(BenchmarkRunner[SimulatorBenchmarkCase]):
    """Runs a simulator benchmark."""

    async def run_benchmark(
        self,
        benchmark_case: SimulatorBenchmarkCase,
        generated_answer: GeneratedAnswer,
    ) -> tuple[BenchmarkResultType, Optional[str], Optional[str], Optional[str]]:
        """Checks if the simulation was successful."""
        
        # 1. Ensure Output is of the correct type
        output, error = await self.ensure_valid_output(
            generated_answer, SimulatorAnswerOutput
        )
        if not output:
             from benchmarks.data_models import BenchmarkErrorType
             return (
                 BenchmarkResultType.FAIL_VALIDATION,
                 f"Failed to parse answer: {error}",
                 None,
                 BenchmarkErrorType.MODEL_INCORRECT_ANSWER,
             )

        # 2. Check Success Status
        if output.is_correct:
             return BenchmarkResultType.PASS, None, None, None
        else:
             from benchmarks.data_models import BenchmarkErrorType
             return (
                 BenchmarkResultType.FAIL_VALIDATION,
                 f"Simulation failed. Transcript available in output.",
                 None,
                 BenchmarkErrorType.TEST_FAILURE
             )
```

### Step 3: Implement the Answer Generator (`benchmarks/answer_generators/simulator_answer_generator.py`)

This is the most critical part. It bridges the two systems.

**Critical Requirements:**
1.  **Sys Path Hack:** `tools/simulator` uses absolute imports (e.g., `import models`). To make this work when imported from `benchmarks`, we must add `tools/simulator` to `sys.path`.
2.  **Async/Sync Bridge:** The simulator code (`SimulationRunner.run`) is synchronous and blocking (it uses `subprocess`). To prevent it from freezing the entire async benchmark runner, we must run it in a separate thread using `loop.run_in_executor`.

**File Content:**

```python
import asyncio
import sys
import os
from typing import Optional, Any
from concurrent.futures import ThreadPoolExecutor

# --- CRITICAL: Path Setup for Simulator Tools ---
# Ensure tools/simulator is in sys.path to support its absolute imports.
# This must happen BEFORE importing anything from tools.simulator.
SIMULATOR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tools/simulator"))
if SIMULATOR_DIR not in sys.path:
    sys.path.insert(0, SIMULATOR_DIR)

from benchmarks.answer_generators.base import AnswerGenerator
from benchmarks.data_models import BaseBenchmarkCase, GeneratedAnswer, SimulatorAnswerOutput, SimulatorBenchmarkCase
from benchmarks.logger import BenchmarkLogger

# Import Simulator tools (these work now because of the sys.path hack)
try:
    from tools.simulator.runner import SimulationRunner as ToolSimulationRunner
    from tools.simulator.models import SimulationResult
except ImportError:
    # Fallback for different execution contexts
    from runner import SimulationRunner as ToolSimulationRunner
    from models import SimulationResult

class SimulatorAnswerGenerator(AnswerGenerator):
    """
    Runs interactive CLI simulations using the tools/simulator harness.
    """
    
    def __init__(self, backend: str = "gemini-cli", logger: Optional[BenchmarkLogger] = None):
        super().__init__(logger)
        self.backend = backend
        # We use a ThreadPoolExecutor to run the blocking simulator code off the main thread.
        self._executor = ThreadPoolExecutor(max_workers=1)

    @property
    def name(self) -> str:
        return f"simulator-{self.backend}"

    @property
    def description(self) -> Optional[str]:
        return f"Runs interactive CLI simulations using the {self.backend} backend."

    async def generate_answer(
        self, benchmark_case: BaseBenchmarkCase, run_id: str
    ) -> GeneratedAnswer:
        # 1. Validate Case Type
        if not isinstance(benchmark_case, SimulatorBenchmarkCase):
             raise ValueError("SimulatorAnswerGenerator only supports SimulatorBenchmarkCase")
        
        loop = asyncio.get_running_loop()
        
        # 2. Define the blocking task
        def _run_sim() -> SimulationResult:
            # This calls the existing simulator logic
            return ToolSimulationRunner.run(benchmark_case.simulation_case, backend=self.backend)

        try:
            # 3. Run in separate thread
            result = await loop.run_in_executor(self._executor, _run_sim)
            
            # 4. Convert result to AnswerOutput
            output = SimulatorAnswerOutput(
                transcript=result.transcript.model_dump(),
                is_correct=result.success,
                rationale=f"Simulation finished with success={result.success}. Backend: {self.backend}"
            )
            
            return GeneratedAnswer(
                output=output,
                raw_output=result.transcript.model_dump_json(),
                usage_metadata=None # Token usage tracking to be added later
            )
            
        except Exception as e:
            return GeneratedAnswer(
                raw_output=f"Simulation crashed: {e}",
                output=None
            )
```

## How to Verify Integration

Since `SimulatorAnswerGenerator` is a standard `AnswerGenerator` and `SimulatorBenchmarkCase` is a standard `BaseBenchmarkCase`, validation should be done using the standard framework tests.

### 1. Verification via `test_unified_generators.py`

This existing test file likely iterates over available generators to ensure they can be instantiated and run against a dummy case.

**Action Required:**
Update `benchmarks/tests/integration/test_unified_generators.py` (or similar) to include a test case for `simulator-gemini-cli`.

**Example Test Addition:**

```python
# In test_unified_generators.py

@pytest.mark.asyncio
async def test_simulator_generator_infrastructure():
    """
    Verifies that the SimulatorAnswerGenerator can run a trivial simulation case.
    We do NOT check for success=True, only that the infrastructure doesn't crash.
    """
    from benchmarks.answer_generators.simulator_answer_generator import SimulatorAnswerGenerator
    from benchmarks.data_models import SimulatorBenchmarkCase
    
    # Need to import these from the tool path or mock them if we can't easily import
    # For integration tests, we assume the environment is set up to allow importing via the generator's path hack.
    # Ideally, define a helper to create the case.
    
    # 1. Create a trivial simulation case
    # We rely on the generator's internal import logic to have set up sys.path 
    # OR we manually set it up here for the test construction
    import sys, os
    SIM_TOOL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../tools/simulator"))
    if SIM_TOOL_PATH not in sys.path:
        sys.path.insert(0, SIM_TOOL_PATH)
        
    from models import InteractiveSimulationCase, ReactorAction, ActionType
    
    sim_case = InteractiveSimulationCase(
        name="Trivial Integration Test",
        initial_prompt="echo 'TEST_INFRA'",
        reactors=[], # No reactors, just run until turn limit or default action
        max_turns=1,
        default_action=ReactorAction(type=ActionType.END_TEST, payload="Done")
    )
    
    bench_case = SimulatorBenchmarkCase(
        id="sim_integration_01",
        simulation_case=sim_case
    )
    
    # 2. Run the generator
    generator = SimulatorAnswerGenerator(backend="gemini-cli")
    result = await generator.generate_answer(bench_case, run_id="test_run")
    
    # 3. Verify Infrastructure Health
    assert result.output is not None, "Generator failed to produce output"
    assert result.output.benchmark_type == "simulator"
    assert "TEST_INFRA" in str(result.output.transcript), "Transcript should capture CLI output"
    
    # NOTE: We do NOT assert result.output.is_correct because the agent might output anything.
    # We only care that the simulator ran and captured the output.
```

### 2. Verification via `run_benchmarks.py`

This is the end-to-end verification.

1.  **Create a Benchmark Definition File:**
    Create a file `benchmarks/benchmark_definitions/debug_suite/simulator_test.yaml` (or Python equivalent if your suite uses code).

2.  **Run the Command:**
    ```bash
    python -m benchmarks.cli.run_benchmarks --suite debug_suite --generator simulator-gemini-cli
    ```

3.  **Expected Output:**
    -   The runner should initialize.
    -   It should pick up the simulator case.
    -   It should launch the simulator (you might see logs from the subprocess).
    -   It should produce a `BenchmarkResult`.
    -   The result status might be `PASS` or `FAIL_VALIDATION` depending on the agent's behavior, but it **MUST NOT be `FAIL_SETUP` or `FAIL_GENERATION`** (which indicate infrastructure crashes).
