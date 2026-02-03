# ADK Benchmark Framework

The ADK Benchmark Framework is a comprehensive system for evaluating, comparing, and validating the performance of AI agents (Answer Generators) against a standardized set of coding and reasoning tasks.

## 🚀 Quick Start

The recommended way to run the full benchmark suite is using the provided CLI tool. This script handles environment setup, execution, and report generation.

```bash
./tools/cli/run_benchmarks.sh
```

This will:
1.  Convert the benchmark runner script into a Jupyter Notebook.
2.  Execute the notebook using `papermill`.
3.  Save the results, including execution traces and a summary report, to a timestamped directory in `benchmark_runs/`.

## 🏗 Architecture

The framework is designed around a modular pipeline:

1.  **Benchmark Definitions** (`benchmark_definitions/`): YAML files defining the test cases (inputs, expected outputs, requirements).
2.  **Answer Generators** (`answer_generators/`): The agents or models being tested. They implement a common interface to accept a prompt and return a solution.
3.  **Orchestrator** (`benchmark_orchestrator.py`): The central engine that loads benchmarks, schedules execution across multiple generators in parallel, and collects results.
4.  **Runners** (`benchmark_runner.py`): Specialized executors for different benchmark types (e.g., `PytestBenchmarkRunner` for code generation tasks).
5.  **Candidates** (`benchmark_candidates.py`): The configuration file where you define *which* agents specifically to test in the current run.

## 📂 Directory Structure

*   `answer_generators/`: Implementations of different agents (e.g., `GeminiAnswerGenerator`, `GeminiCliPodmanAnswerGenerator`).
*   `benchmark_definitions/`: The actual test cases, organized by category (e.g., `fix_errors`, `api_understanding`).
*   `generator/`: Tools for procedurally generating benchmark cases.
*   `ground_truth/`: Correct reference implementations for validation.
*   `tests/`: Unit and integration tests *for the framework itself*.
*   `traces/`: Temporary storage for execution traces.

## ⚙️ Configuration

### Selecting Agents to Benchmark

To modify which agents are evaluated, edit **`benchmarks/benchmark_candidates.py`**.

The `CANDIDATE_GENERATORS` list determines the active set of agents for the next run. You can uncomment existing configurations or add new ones:

```python
# benchmarks/benchmark_candidates.py

CANDIDATE_GENERATORS = [
    # ... other agents ...
    GeminiCliPodmanAnswerGenerator(
        image_definitions=IMAGE_DEFINITIONS,
        image_name="gemini-cli:mcp_adk_agent_runner_ranked_knowledge",
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager,
        experiment_id="ranked_knowledge_vector",
    ),
]
```

### API Keys

Ensure you have your API keys set in your environment or `.env` file, particularly `GEMINI_API_KEY`, as most agents rely on it.

## 🧪 Validating the Framework

Before running expensive experiments, you should verify that the benchmarks themselves are valid and the runners are working correctly. We provide a suite of integration tests for this purpose.

**Run validation tests:**
```bash
python -m pytest benchmarks/tests/integration/test_baseline_generators.py
```
This runs the `GroundTruthAnswerGenerator` (which should always pass) to confirm the system is healthy.

## 🛠 Extending the Framework

### Adding a New Benchmark Case

1.  **Fix Error Cases**: Add a new directory in `benchmarks/benchmark_definitions/fix_errors/cases/` containing:
    *   `unfixed.py`: The broken code.
    *   `fixed.py`: The correct code.
    *   `test_agent.py`: A pytest file to verify the solution.
    *   Then, register it in `benchmarks/benchmark_definitions/fix_errors/benchmark.yaml`.

2.  **Multiple Choice**: Add a new entry to the relevant YAML file (e.g., `benchmarks/benchmark_definitions/api_understanding/benchmark.yaml`).

### Adding a New Agent

Create a new class inheriting from `AnswerGenerator` in `benchmarks/answer_generators/`. Implement the `generate_answer` method. Then, add an instance of it to `benchmarks/benchmark_candidates.py`.

## 🔧 Troubleshooting

### Podman Issues

The framework uses Podman for isolated execution of generated code. If you encounter connection errors or timeouts:

1.  **Restart the Podman machine:**
    ```bash
    podman machine stop
    podman machine start
    ```
2.  **Check Resources:** Ensure your Podman machine has at least 16GB of RAM.
    ```bash
    podman machine set --memory 16384
    ```
