# Tools & Utilities

This directory contains helper scripts and tools for analyzing benchmarks, debugging agents, and managing the repository.

## Primary Tools

-   **`cli/audit_failures.py`**: The "Mechanic." 
    -   **Mechanism**: **Deterministic**. 
    -   Uses Regex pattern matching to classify errors and Heuristic timeline analysis to detect architectural bugs (e.g., "Early Loop Exits").
    ```bash
    python tools/cli/audit_failures.py --inspect "case_name"
    ```

-   **`cli/generate_benchmark_report.py`**: The "Journalist."
    -   **Mechanism**: **Hybrid (Stats + LLM)**.
    -   Uses an LLM to perform a multi-stage reduction:
        1. **Map**: Audits every individual attempt trace in parallel.
        2. **Reduce**: Synthesizes attempt-level insights into Case-level patterns.
        3. **Finalize**: Aggregates all data into the high-level `log_analysis.md` executive summary.
    -   **Output**: Includes a "Report Generation Metadata" section tracking latency, tokens, and LLM calls cost for the analysis itself.
    ```bash
    python tools/cli/generate_benchmark_report.py [run_id]
    ```

-   **`analysis/analyze_case_quality.py`**: The "Auditor."
    -   **Mechanism**: **Hybrid (DB + LLM)**.
    -   Identifies repeatedly failing benchmark cases from the history database and uses an LLM to determine if the test case itself is flawed (ambiguous, incorrect ground truth) or if it's a genuine agent failure.
    ```bash
    python tools/analysis/analyze_case_quality.py
    ```

-   **`benchmark_viewer.py`**: Streamlit-based TUI. Integrates the Auditor engine for on-demand visual forensics.

## Analysis Hierarchy & Mechanisms

```text
[TOOL]                            [BACKEND MODULE]                   [MECHANISM]
generate_benchmark_report.py  -> analyze_benchmark_run.py ---------> Map-Reduce (LLM Reasoning)
audit_failures.py             ->   └── analyze_generator.py -------> Deterministic Math (Stats)
benchmark_viewer.py           ->       └── analyze_case.py --------> Regex (Error Classification)
                                           └── analyze_attempt.py -> Heuristic (Event Auditing)
```

### Reporting Pipeline Logic (Map-Reduce)

```python
# Level 1: Map (Parallel Audit)
for attempt in all_failed_attempts:
    insight = LLM.analyze(
        trace=attempt.logs,
        prompt="Find exact failure point"
    ) # -> ForensicInsight

# Level 2: Reduce (Case Synthesis)
for case, insights in group_by_benchmark(insights):
    case_summary = LLM.summarize(
        insights=insights,
        prompt="Identify behavioral trajectory (regressing vs closer)"
    ) # -> CaseSummary

# Level 3: Final Reduce (Run Executive Summary)
report = LLM.generate_final_report(
    stats=deterministic_quantitative_metrics,
    case_summaries=all_case_summaries,
    prompt="Write executive summary and actionable recommendations"
) # -> log_analysis.md
```

## Subdirectories

### `analysis/`
The core engine for understanding agent performance. See [tools/analysis/README.md](analysis/README.md) for logic details.
-   **`analyze_benchmark_run.py`**: Orchestrates the analysis of a complete run.
-   **`analyze_generator.py`**: Calculates metrics (Pass Rate, Cost) per generator.
-   **`analyze_case.py`**: Aggregates multi-attempt history for a single benchmark.
-   **`analyze_attempt.py`**: Deep-dive heuristic audit of a single execution trace.

### `utils/`
Miscellaneous utility scripts.
-   `finalize_prismatic_benchmarks.py`: Helper for dataset generation.

## Legacy / Experimental
-   `api_indexer.py`, `generate_adk_index.py`: Tools for building the ADK knowledge index.
-   `graph_adk_structure.py`: Visualizes the ADK codebase structure.
