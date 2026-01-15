# Prismatic Evaluation Generator

This module implements the **Prismatic Evaluation** architecture for generating repository-specific benchmarks using the ADK framework.

## Architecture

The system follows a closed-loop design with specialized pipelines for different benchmark types:

### Pipelines

1.  **Execution MCQ (`execution_mcq`)**
    *   `Observer` -> `Saboteur` -> `Referee` -> `Critic` -> `Assembler`
    *   Established "Golden" behavior via real execution.
    *   Iteratively refines distractors until they pass sandbox verification.

2.  **Conceptual MCQ (`concept_mcq`)**
    *   `Analyst` -> `Confabulator` -> `Reviewer` -> `Critic` -> `Assembler`
    *   Focuses on architectural and design responsibilities.
    *   Includes a deduplication step to ensure semantic uniqueness across the suite.

## Deep Dive: Strategy Layer (The Auditor)

The **Auditor** agent orchestrates the entire process, spending compute on high-value targets via a stateful BFS strategy.

### 1. Repository Cartography
The `scan_repository` tool maps the repository topology using AST analysis, identifying hierarchies, dependencies, and public API surfaces while calculating a Cyclomatic Complexity heuristic.

### 2. BFS Prioritization Strategy
The system generates a deterministic queue based on the following priority:

1.  **Seeds (High Usage)**: Modules/classes with `usage_score > 0` in `adk_stats.yaml`, ranked by usage frequency.
2.  **Dependencies**: For every seed, the system performs a **Breadth-First Search (BFS)** to identify all internal dependencies. This ensures that core infrastructure is tested before edge cases.
3.  **Orphans**: Any remaining public entities (zero usage, no internal inbound dependencies) are appended to the end, ranked by complexity.

The queue is computed once per session and cached in the SQLite database for consistency and performance.

## Reliability & Debugging

### 1. Structured Tracing
Every generation run produces a `generation_trace.jsonl` file in the output directory. This log captures:
*   **Target Selection**: Why a specific target was chosen and the current state of the queue.
*   **Benchmark Completion**: When a case is saved, including coverage statistics.

### 2. Resumption (Crash-Safety)
The generator is designed to be resumed after an interruption (e.g., rate limits, crashes, or user-cancel).

**To Resume:** Simply re-run the **exact same command**. The system will:
1.  Reload the cached BFS queue from the `--session-db`.
2.  Synchronize progress from `processed_targets.json` in the `--output-dir`.
3.  Continue from the next unprocessed target.

## Usage

To generate conceptual benchmarks for the ADK:

```bash
PYTHONPATH=. env/bin/python benchmarks/benchmark_generator/run_generator.py \
    --type prismatic_adk \
    --mode concept_mcq \
    --repo-path ../adk-python \
    --namespace google.adk \
    --output-dir benchmarks/benchmark_definitions/my_suite \
    --model-name gemini-3-pro-preview \
    --limit 100 \
    --session-db prismatic_sessions.db
```

## Structure

*   `agents.py`: MAS orchestration (Sequential, Loop, and Specialized Agents).
*   `tools.py`: Core logic (Cartographer, BFS Strategist, Truth Lab, Sandbox).
*   `logger.py`: Colored console logging and structured file tracing.
*   `irt.py`: IRT-based prioritization scoring (Legacy support).
