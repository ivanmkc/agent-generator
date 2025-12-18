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

## Manual Podman Image Builds

The benchmark suite utilizes several Podman (or Docker-compatible) images for different Gemini CLI configurations. These images are typically built automatically during the benchmark setup phase. However, if you need to build them manually (e.g., for debugging build issues or pre-populating your local image registry), follow these steps from the project root directory:

**1. `gemini-cli:base`**
This is the foundational image for the Gemini CLI server.
```bash
podman build -t gemini-cli:base -f benchmarks/answer_generators/gemini_cli_docker/base/Dockerfile benchmarks/answer_generators/gemini_cli_docker/base
```

**2. `gemini-cli:adk-python`**
This image extends the base image and includes the ADK Python extension.
```bash
podman build -t gemini-cli:adk-python -f benchmarks/answer_generators/gemini_cli_docker/adk-python/Dockerfile --build-arg BASE_IMAGE=gemini-cli:base benchmarks/answer_generators/gemini_cli_docker/adk-python
```

**3. `gemini-cli:mcp-context7`**
This image extends the base image and includes the MCP Context7 extension.
```bash
podman build -t gemini-cli:mcp-context7 -f benchmarks/answer_generators/gemini_cli_docker/gemini-cli-mcp-context7/Dockerfile --build-arg BASE_IMAGE=gemini-cli:base benchmarks/answer_generators/gemini_cli_docker/gemini-cli-mcp-context7
```

**4. `gemini-cli:adk-docs-ext`**
This image extends the base image and includes the ADK Docs extension.
```bash
podman build -t gemini-cli:adk-docs-ext -f benchmarks/answer_generators/gemini_cli_docker/adk-docs-ext/Dockerfile --build-arg BASE_IMAGE=gemini-cli:base benchmarks/answer_generators/gemini_cli_docker/adk-docs-ext
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
