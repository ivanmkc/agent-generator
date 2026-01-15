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
Specialized scripts for deep-diving into benchmark results and agent behavior. See [tools/analysis/README.md](analysis/README.md) for more details.
-   **`analyze_root_causes.py`**: Automated failure classification and DB ingestion.
-   **`llm_root_cause_analysis.py`**: LLM-powered forensic audit of failed traces.
-   **`analyze_tool_failures.py`**: Statistical reporting on failure modes.
-   **`analyze_benchmark_chunks.py`**: Per-case comparison of tokens and duration.
-   **`compare_tool_usage.py`**: Detailed token efficiency comparison between runs.
-   **`deep_dive_tool_params.py`**: Tool chain extraction for specific failures.
-   **`analyze_results_json.py`**, `analyze_traces.py`: Quick diagnostic scripts.
-   **`compare_adk_variants.py`**: Side-by-side agent performance comparison.

### `utils/`
Miscellaneous utility scripts.
-   `finalize_prismatic_benchmarks.py`: Helper for dataset generation.

## Legacy / Experimental
-   `api_indexer.py`, `generate_adk_index.py`: Tools for building the ADK knowledge index.
-   `graph_adk_structure.py`: Visualizes the ADK codebase structure.
