# Tools & Utilities

This directory contains helper scripts and tools for analyzing benchmarks, debugging agents, generating datasets, and managing the repository.

## Primary Tools

### Benchmark Generation
-   **`benchmarks.generator.benchmark_generator/`**: The Agentic Benchmark Generator.
    -   **Mechanism**: **Autonomous Agentic**.
    -   Uses a multi-agent system (Auditor, Observer, Saboteur, Referee) to generate code-based benchmarks from the repository itself.
    -   See [benchmarks.generator.benchmark_generator/README.md](benchmark_generator/README.md).

-   **`tools/knowledge/target_ranker/`**: The Target Ranker.
    -   **Mechanism**: **Deterministic Static Analysis**.
    -   Scans the repository, resolves inheritance, and ranks targets for benchmark generation based on usage statistics.
    -   See [tools/knowledge/target_ranker/README.md](target_ranker/README.md).

### Analysis & Reporting
-   **`cli/audit_failures.py`**: The "Mechanic." 
    -   **Mechanism**: **Deterministic**. 
    -   Uses Regex pattern matching to classify errors and Heuristic timeline analysis to detect architectural bugs.
    ```bash
    python tools/cli/audit_failures.py --inspect "case_name"
    ```

-   **`cli/generate_benchmark_report.py`**: The "Journalist."
    -   **Mechanism**: **Hybrid (Stats + LLM)**.
    -   Uses an LLM to perform a multi-stage reduction (Map-Reduce) to synthesize insights.
    ```bash
    python tools/cli/generate_benchmark_report.py [run_id]
    ```

-   **`viewer/benchmark_viewer.py`**: Streamlit-based TUI for visual forensics.

## Directory Structure

*   `analysis/`: Analysis engine for understanding agent performance.
*   `benchmark_generator/`: The Agentic Benchmark Generator module.
*   `target_ranker/`: Static analysis tool for ranking codebase targets.
*   `benchmark_verification/`: Tools for validating benchmark integrity.
*   `cli/`: Command-line interfaces for analysis tools.
*   `debugging/`: Scripts for debugging specific runs or failures.
*   `knowledge/`: Tools for indexing and analyzing the ADK knowledge base.
*   `retrieval_dataset_generation/`: Tools for creating RAG datasets.
*   `adk-knowledge-ext/`: ADK Knowledge extensions.
*   `viewer/`: Visualization tools (Streamlit).
*   `utils/`: Miscellaneous scripts.

## Legacy / Experimental
-   `extract_potential_frameworks.py` (Moved to `vibeshare/scripts/`)\n## Testing\n\nTo run tests for all tools:\n```bash\npython -m pytest tools/\n```
