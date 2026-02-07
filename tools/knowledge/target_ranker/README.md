# Target Ranker

The **Target Ranker** is a specialized tool module responsible for scanning a Python repository, resolving its structure (inheritance, signatures), and prioritizing entities (classes, methods) for benchmark generation.

## Purpose

It acts as the "Cartographer" for the Agentic Benchmark Generator, providing a structured map of the codebase and a prioritized list of targets based on usage statistics.

## Components

*   **`ranker.py`**: The main entry point. Orchestrates scanning, inheritance resolution, and ranking by applying weights from co-occurrence and usage patterns.
*   **`scanner.py`**: Contains `scan_repository`, which uses AST analysis to parse Python files, resolve types, and build a raw structure map.
*   **`models.py`**: Defines the data models (`RankedTarget`, `MemberInfo`) used for the final output.
*   **`run_cooccurrence_indexing.py`** (upstream module): Scans raw codebases to generate a `cooccurrence.yaml` conditional probability matrix linking components together (e.g. `pydantic` usages with `google.genai`).

## Co-occurrence & Sample Repo Architecture

During codebase indexing, we need to know not just *what* classes exist, but *how they are used*. A large part of this comes from mining external codebases that use the target library.

1. **`registry.yaml` Definitions**: In `tools/adk_knowledge_ext/src/adk_knowledge_ext/registry.yaml`, target libraries define `sample_repos` (e.g., `adk-samples`).
2. **`manage_registry.py` Execution**: When updating an index, the automated pipeline shallow-clones the target library's source code AND any defined `sample_repos` into temporary directories.
3. **Probability Mining**: `tools/knowledge/run_cooccurrence_indexing.py` is invoked across all these cloned codebases. It uses "Dynamic Namespace Discovery" (ignoring standard library packages like `sys`) to track component interactions across files, outputting `cooccurrence.yaml`.
4. **Resolution filtering**: Because sample repositories may use outdated versions of the target library, `ranker.py` acts as a safeguard. It rigidly maps only the classes that exist in the *current* checked-out library version, matching the "loose" heuristics of `cooccurrence.yaml` against its strict map, silently dropping legacy or hallucinated functions.

## Usage

This module is typically invoked via the `Regenerate Ranked Targets` task in `.vscode/tasks.json`.

To run standalone via the CLI:

```bash
env/bin/python tools/knowledge/target_ranker/run_ranker.py --repo-path repos/adk-python
```

## Output

It generates artifacts in the centralized output directory (managed by `tools/constants.py`):
*   `tmp/outputs/generated_benchmarks/ranked_targets.yaml`: Detailed metadata for agents.
*   `tmp/outputs/generated_benchmarks/ranked_targets.md`: Human-readable summary.
\n## Testing\n\nRun the unit tests:\n```bash\npython -m pytest tools/knowledge/target_ranker/tests/\n```
