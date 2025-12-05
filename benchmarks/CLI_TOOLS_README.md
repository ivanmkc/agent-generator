# Gemini CLI Tools

This folder contains helper scripts for running benchmarks and converting Python scripts to Jupyter notebooks, specifically tailored for the ADK environment.

## Scripts

### 1. `benchmark_run.py`

A standalone Python script to execute the full suite of benchmarks against configured Answer Generators (GroundTruth, Trivial, Gemini SDK, and Gemini CLI).

**Features:**
- Runs benchmarks in parallel (configurable concurrency).
- Categorizes errors into "Model Failures" vs "Infrastructure Failures".
- Prints a detailed summary table and failure logs.

**Usage:**
```bash
# Run directly (if not inside an existing event loop)
env/bin/python benchmarks/benchmark_run.py
```

### 2. `convert_py_to_ipynb.py`

A utility script to convert `benchmark_run.py` (or similar scripts) into a Jupyter Notebook (`.ipynb`).

**Why is this needed?**
- `papermill` executes notebooks, which run inside an existing event loop (`ipykernel`).
- Scripts using `asyncio.run()` fail inside notebooks with `RuntimeError`.
- This script automatically replaces `asyncio.run(main())` with `await main()`, making the code compatible with the notebook environment.

**Usage:**
```bash
# Converts benchmark_run.py -> benchmark_run.ipynb
cd benchmarks
../env/bin/python convert_py_to_ipynb.py
```

## Workflow

To run benchmarks via `papermill`:

1.  Navigate to this directory or ensure scripts are accessible.
2.  Convert the runner script to a notebook:
    ```bash
    env/bin/python benchmarks/convert_py_to_ipynb.py
    ```
3.  Execute the notebook:
    ```bash
    TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S) && mkdir -p benchmark_runs/$TIMESTAMP && \
    env/bin/papermill benchmark_run.ipynb benchmark_runs/$TIMESTAMP/output.ipynb --cwd . -k python3
    ```
