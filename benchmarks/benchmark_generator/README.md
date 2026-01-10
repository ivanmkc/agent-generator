# Prismatic Evaluation Generator

This module implements the **Prismatic Evaluation** architecture for generating repository-specific benchmarks using the ADK framework.

## Architecture

The system follows a closed-loop design with four phases:

1.  **Phase 0: Strategy (Auditor)**
    *   **Goal**: Map the territory and select the most valuable targets.
    *   **Scanner (Cartographer)**: Uses AST analysis to map the repository topology.
    *   **Prioritization**: Selects targets based on Information Theory and Code Coverage.

2.  **Phase 1: Truth Lab (Observer)**
    *   **Goal**: Establish Ground Truth.
    *   Generates valid usage code (Golden Snapshot) for the selected target.
    *   Validates the code execution using the `trace_execution` tool (capturing stdout/locals).

3.  **Phase 2: Adversarial Forge (Saboteur & Referee)**
    *   **Goal**: Create Hard Negatives.
    *   **Saboteur**: Generates mutants using three strategies (Semantic Mutation, Context Poisoning, Structure Masking).
    *   **Referee**: Validates that mutants fail (or behave differently) using the `validate_mutant` tool. If validation fails, it triggers a revision loop.

4.  **Phase 3: Quality & Assembly (Critic & Assembler)**
    *   **Goal**: Ensure quality and uniqueness.
    *   **Critic**: Checks for duplicates using Jaccard similarity.
    *   **Assembler**: Combines the Golden Snapshot and valid Mutants into a `MultipleChoiceBenchmarkCase`.

## Deep Dive: Strategy Layer

The **Strategy Layer** is the brain of the operation, ensuring that compute is spent on the most critical and uncovered parts of the codebase.

### 1. `scan_repository` (The Cartographer)
This tool performs a static analysis of the repository to build a "Map" of testable units. It goes beyond simple file listing:

*   **Topology Mapping**: It uses Python's `ast` module to walk the Abstract Syntax Tree of every file.
*   **Hierarchy Extraction**: For every class found, it extracts the `parent_classes` to understand the inheritance tree.
*   **Dependency Graph**: It parses all `import` statements (`ast.Import`, `ast.ImportFrom`) to list dependencies for each file.
*   **API Surface Identification**: It filters for public methods (ignoring `_private`), captures their signatures and docstrings, and calculates a **Cyclomatic Complexity** heuristic.

    **Complexity Scoring (Heuristic):**
    *   **Formula**: `end_lineno - lineno` (Total lines of code in the function definition).
    *   **Reasoning**: While true Cyclomatic Complexity measures independent paths, raw line count is a robust, zero-cost proxy for identifying substantive logic vs. trivial one-liners (getters/setters).
    *   **Threshold**: Methods with `< 3` lines are automatically discarded to prevent benchmark bloat.

*   **Coverage Injection**: If a `coverage.json` file is provided, it maps coverage statistics to each target file.

### 2. `get_prioritized_target` (The Strategist)
This tool implements the **Item Response Theory (IRT)** logic to select the next best target. It uses a scoring function to maximize the "Fisher Information" (value) of the benchmark.

**The Scoring Formula:**
`Priority = Complexity + CoverageScore + IRTScore + DocBonus`

*   **Complexity**: Higher complexity -> Higher priority (more logic to test).
*   **CoverageScore**: 
    *   If file is **Uncovered**: `+50` points.
    *   If file is **Covered**: `-50` points (prioritizing the unknown).
*   **IRTScore**: Calculated using the `IRTManager` based on historical data (if `irt_file` provided):
    *   `10 * Discrimination + 5 * Difficulty`
    *   Targets that have historically discriminated well between capable and incapable agents are prioritized.
*   **DocBonus**: `+10` points if the method has a docstring (making it a better candidate for "Golden" generation).

## Coverage Methodology

The Prismatic Generator uses **Code Coverage** as a primary signal to direct the `Auditor` towards untested logic.

### Ingestion
Coverage data is ingested via the `--coverage-file` argument. The system expects a JSON file (standard output from tools like `coverage.py json`).

**Supported Format:**
```json
{
  "meta": { ... },
  "files": {
    "path/to/file.py": {
      "executed_lines": [1, 2, 5],
      "missing_lines": [3, 4],
      "excluded_lines": [],
      "summary": {
        "covered_lines": 3,
        "num_statements": 5,
        "percent_covered": 60.0
      }
    }
  }
}
```

### Prioritization Logic
The `scan_repository` tool reads this file and maps coverage status to each scanned target method based on its `file_path`.

The `IRTManager` (used by `get_prioritized_target`) calculates a **Coverage Score**:
1.  **Uncovered Files**: If a file is *not present* in the coverage report (or has low coverage), it receives a massive priority boost (`+50 points`). This forces the generator to focus on "dark matter"—code that is currently invisible to the test suite.
2.  **Covered Files**: If a file is present (implying existing tests), it receives a penalty (`-50 points`). This ensures we don't waste tokens generating benchmarks for code that is already well-tested.

### Verification
To verify coverage integration:
1.  Generate a coverage report: `coverage run -m pytest && coverage json`
2.  Run the generator: `python .../run_generator.py ... --coverage-file coverage.json`
3.  The `Auditor` logs will show it prioritizing files absent from `coverage.json`.

## Usage

To generate benchmarks for the current repository:

```bash
PYTHONPATH=. env/bin/python benchmarks/benchmark_generator/run_generator.py \
    --type prismatic_adk \
    --output-dir benchmarks/benchmark_definitions/prismatic_generated \
    --model gemini-3-pro-preview \
    --repo-path . \
    --coverage-file coverage.json
```

## Structure

*   `agents.py`: Defines the ADK Agents (`Auditor`, `Observer`, `Saboteur`, `Referee`, `Critic`, `Assembler`) and the Workflow (`PrismaticLoop`).
*   `tools.py`: Implements the core logic tools (`scan_repository`, `get_prioritized_target`, `trace_execution`, `validate_mutant`, `check_uniqueness`).
*   `irt.py`: Implements the IRT scoring logic.
*   `models.py`: Pydantic models for inter-agent communication.
*   `logger.py`: Custom colored logger for the multi-agent loop.
