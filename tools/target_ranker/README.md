# Target Ranker

The **Target Ranker** is a specialized tool module responsible for scanning a Python repository, resolving its structure (inheritance, signatures), and prioritizing entities (classes, methods) for benchmark generation.

## Purpose

It acts as the "Cartographer" for the Agentic Benchmark Generator, providing a structured map of the codebase and a prioritized list of targets based on usage statistics.

## Components

*   **`ranker.py`**: The main entry point. Orchestrates scanning, inheritance resolution, and ranking.
*   **`scanner.py`**: Contains `scan_repository`, which uses AST analysis to parse Python files, resolve types, and build a raw structure map.
*   **`models.py`**: Defines the data models (`RankedTarget`, `MemberInfo`) used for the final output.

## Usage

This module is typically invoked via the `Regenerate Ranked Targets` task in `.vscode/tasks.json`.

To run standalone via the CLI:

```bash
env/bin/python tools/target_ranker/run_ranker.py --repo-path repos/adk-python
```

## Output

It generates artifacts in the centralized output directory (managed by `tools/constants.py`):
*   `tmp/outputs/generated_benchmarks/ranked_targets.yaml`: Detailed metadata for agents.
*   `tmp/outputs/generated_benchmarks/ranked_targets.md`: Human-readable summary.
\n## Testing\n\nRun the unit tests:\n```bash\npython -m pytest tools/target_ranker/tests/\n```
