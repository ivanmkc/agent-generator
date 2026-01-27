# Target Ranker

The **Target Ranker** is a specialized tool module responsible for scanning a Python repository, resolving its structure (inheritance, signatures), and prioritizing entities (classes, methods) for benchmark generation.

## Purpose

It acts as the "Cartographer" for the Agentic Benchmark Generator, providing a structured map of the codebase and a prioritized list of targets based on usage statistics.

## Components

*   **`ranker.py`**: The main entry point. Orchestrates scanning, inheritance resolution, and ranking.
*   **`scanner.py`**: Contains `scan_repository`, which uses AST analysis to parse Python files, resolve types, and build a raw structure map.
*   **`models.py`**: Defines the data models (`RankedTarget`, `MemberInfo`) used for the final output.

## Usage

This module is typically invoked via the `Regenerate Ranked Targets` task in `.vscode/tasks.json` or by the Benchmark Generator agents.

To run standalone:

```bash
PYTHONPATH=. env/bin/python tools/target_ranker/ranker.py
```

(Note: Ensure `benchmarks/adk_stats_samples.yaml` exists if using default stats file).

## Output

It generates:
*   `tools/benchmark_generator/data/ranked_targets.yaml`: Detailed metadata for agents.
*   `tools/benchmark_generator/data/ranked_targets.md`: Human-readable summary.
\n## Testing\n\nRun the unit tests:\n```bash\npython -m pytest tools/target_ranker/tests/\n```
