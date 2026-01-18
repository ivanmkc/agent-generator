# ADK Benchmark & Agent Generator

This repository contains the benchmarking framework for Google's Agent Development Kit (ADK). It includes tools for generating agents, running benchmarks, and performing deep forensic analysis on the results.

## Quick Start

### 1. Run Benchmarks
Use the orchestrator to run a suite of tests.
```bash
./notebooks/run_benchmarks.sh
```

### 2. View Results
Launch the interactive dashboard to browse results.
```bash
streamlit run tools/benchmark_viewer.py
```

### 3. Forensic Analysis
Diagnose failures using the unified forensic pipeline.

*   **Audit Failures (Deterministic):**
    ```bash
    python tools/cli/audit_failures.py
    ```
*   **Generate Report (LLM Map-Reduce):**
    ```bash
    python tools/cli/generate_benchmark_report.py
    ```

## Project Structure

*   `benchmarks/`: Core benchmark definitions and runner logic.
*   `tools/`: CLI tools for analysis and debugging.
    *   `tools/cli/`: Executable scripts (`audit_failures.py`, `generate_benchmark_report.py`).
    *   `tools/analysis/`: Shared analysis engine (`analyze_benchmark_run.py`, etc.).
*   `notebooks/`: Jupyter notebooks for data science and visualization.

See [tools/README.md](tools/README.md) for detailed architecture documentation.
