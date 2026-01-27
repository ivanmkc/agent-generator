# Benchmark Analysis Library

This directory contains the modular engine used by all diagnostic and reporting tools. It breaks down raw `trace.yaml` data into a meaningful hierarchy.

## 1. Modular Hierarchy & Mechanisms

*   **`run_metrics.py`**: **Orchestrator**. Parses `results.json` and maps data into the hierarchical object model.
*   **`generator_performance.py`**: **Quantitative Stats**. Deterministic calculation of pass rates, latency, and estimated cost (blended input/output rate).
*   **`case_inspection.py`**: **Regex Classifier**. Categorizes failures by matching validation error strings against known patterns:
    *   `Malformed JSON`: Parsing failures in model output.
    *   `Interface Violation`: Missing required methods (e.g., `create_agent`).
    *   `Syntax Error`: Syntactically invalid Python code.
    *   `Infrastructure Error`: 429 Resource Exhaustion or Quota limits.
*   **`attempt_forensics.py`**: **Heuristic Auditor**. Scans the chronological event timeline of a single trace to detect specific agent "brain-farts":
    *   **Early Loop Exit**: Detects when a `retrieval_worker` calls `exit_loop` and terminates the implementation sequence before code is generated.
    *   **Sanitizer Hallucination**: Detects when the `prompt_sanitizer` outputs a JSON answer structure instead of cleaning the text.
    *   **Router Decision**: Extracts the 'CODING' vs 'KNOWLEDGE' path chosen for the task.

## 2. LLM Map-Reduce Pipeline

For complex failures, the reporter uses a multi-stage LLM pipeline (`gemini-2.0-pro-exp-02-05`) to extract semantic meaning from raw traces:

### Level 1: Map (Attempt Audit)
*   **Logic**: Every failed attempt trace is serialized (truncated if necessary) and audited.
*   **Output**: `ForensicInsight` (Root cause category, precise narrative, and evidence list).

### Level 2: Reduce (Case Synthesis)
*   **Logic**: Aggregates all `ForensicInsight` objects for a specific benchmark.
*   **Output**: `CaseSummary` (Recurring failure patterns and behavioral progression, e.g., "Drifting from goal", "Stuck in retrieval loop").

### Level 3/4: Final Reduction (Run Summary)
*   **Logic**: The high-level reporter consumes these structured summaries to write the final executive summary and actionable recommendations.

## 3. Shared Usage

These modules are designed to be imported, not run directly.

```python
from tools.analysis.run_metrics import analyze_benchmark_run

# 1. Load and process the run
run = analyze_benchmark_run("2026-01-16_23-39-35")

# 2. Access metrics
for gen in run.generators.values():
    print(f"{gen.name}: {gen.pass_rate}%")

# 3. Check for architectural bugs
alerts = run.get_critical_alerts()
```

These tools work directly on `trace.yaml` files without needing the database.

### `chunk_metrics.py`
Parses a raw trace file and outputs a clean Markdown table of every benchmark case, its pass/fail status, token usage, and duration.

**Usage:**
```bash
python tools/analysis/chunk_metrics.py <path_to_trace.yaml>
```

**Example:**
```bash
python tools/analysis/chunk_metrics.py benchmark_runs/2026-01-13_04-07-18/trace.yaml
```

**Output:**
```text
Benchmark Case                                     | Generator                                | Status     | Tokens     | Time (s)  
========================================================================================================================
01: A minimal LlmAgent...                          | ADK_STATISTICAL_V41                      | PASS       | 4032       | 12.50     
02: A tool-using agent...                          | ADK_STATISTICAL_V41                      | FAIL       | 15201      | 45.20     
```

### `analyze_traces.py`
A lightweight script to filter traces for specific events (like specific tool calls).
*   **Usage:** Requires editing the `log_file` variable in the `__main__` block.
*   **Goal:** Quickly checking "Which benchmarks actually called `run_adk_agent`?"

---

## 3. Comparison & Advanced Tools

These scripts are often used as templates or require specific configuration for A/B testing.

### `compare_adk_variants.py`
Runs two different agent configurations side-by-side against the same benchmark suite.
*   **Usage:** Edit the `candidate_1` and `candidate_2` definitions in the script, then run.
*   **Output:** Generates a combined trace log in `tmp/compare_logs/`.

### `compare_tool_usage.py`
Analyzes two trace files and compares the "Token Efficiency" of their tool usage (i.e., how verbose were the tool outputs vs. how useful they were).
*   **Usage:** Edit the file paths in the `__main__` block:
    ```python
    analyze_trace("path/to/run_A/trace.yaml", "Variant A")
    analyze_trace("path/to/run_B/trace.yaml", "Variant B")
    ```

---

## Database Schema (`benchmarks/analysis_cache.db`)

If you want to write custom SQL queries, the schema is:

*   **`failures` Table:**
    *   `run_id`: Timestamp string of the run.
    *   `benchmark_name`: Name of the test case.
    *   `error_type`: JSON list of regex-detected tags.
    *   `llm_root_cause`: The LLM's final verdict (e.g., "Reasoning: Ignored Context").
    *   `llm_analysis`: Full JSON output from the forensic agent.
    *   `explanation`: Brief error snippet.
