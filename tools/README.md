# Tools & Utilities

This directory contains helper scripts and tools for analyzing benchmarks, debugging agents, and managing the repository.

## Primary Tools

-   **`debugging.py`**: The main debugging CLI. Use this to inspect failed benchmark cases and generate deep-dive analysis reports.
    ```bash
    python tools/debugging.py --run-dir benchmark_runs/<timestamp> --list-cases
    python tools/debugging.py --run-dir benchmark_runs/<timestamp> --case "Case Name" --report
    ```

-   **`benchmark_viewer.py`**: A TUI (Text User Interface) for browsing benchmark results.
    ```bash
    python tools/benchmark_viewer.py
    ```

## Subdirectories

### `analysis/`
Scripts for aggregated analysis of benchmark data.
-   `analyze_results_json.py`: Parses `results.json` to compute aggregate metrics.
-   `compare_adk_variants.py`: Compares performance across different ADK agent versions.
-   `analyze_traces.py`: detailed inspection of trace logs.

### `utils/`
Miscellaneous utility scripts.
-   `finalize_prismatic_benchmarks.py`: Helper for dataset generation.

## Legacy / Experimental
-   `api_indexer.py`, `generate_adk_index.py`: Tools for building the ADK knowledge index.
-   `graph_adk_structure.py`: Visualizes the ADK codebase structure.
