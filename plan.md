# Development Plan: Advanced Statistical API Discovery Agent

## 1. Current Progress Summary
*   **Architecture Defined:** Established the **Single-Agent ReAct Solver** as the leading archetype for token efficiency (< 15k tokens) and zero-knowledge compliance.
*   **Verification Criteria:** Formalized `VERIFICATION_CRITERIA.md` to enforce strict generalization (no hardcoded API hints in prompts).
*   **Advanced Tooling implemented:**
    *   `tools/api_indexer.py`: AST-based statistical analyzer to establish idiomatic "Happy Path" API usage.
    *   `tools/debugging.py`: Granular trace analyzer to diagnose tool-usage errors and hallucinations.
    *   `get_module_help` (v2): Enhanced runtime inspection with recursive depth and signature extraction.
*   **Root Cause Identified:** Benchmark failures (Experiment 16-19) are primarily due to **Pydantic field-name strictness** and shallow exploration (guessing parameters instead of verifying implementation modules).

## 2. Architecture: Single-Agent ReAct Solver
The agent follows a **Map -> Navigate -> Implement** loop:
1.  **Map:** Discovers the high-level module structure.
2.  **Navigate:** Uses `get_module_help` (statistical) to identify mandatory vs. optional parameters based on real-world usage frequencies.
3.  **Implement:** Generates code using verified signatures, minimizing `ValidationError` regressions.

## 3. Immediate Next Steps

### Step 1: Statistical Indexing
Run the indexer on core repositories to seed the "Conditional Probability" of argument usage.
*   Target: `google/adk-python` (Core)
*   Target: `google/adk-samples/python/examples` (Idiomatic usage)
*   Output: `benchmarks/adk_stats.yaml`

### Step 2: Experiment 20 (Statistical Discovery)
Enable the agent to consume the statistical index.
*   **Tool:** Update `AdkTools` to prioritize arguments with high usage frequency (e.g., > 20% in samples).
*   **Verification:** Run against `fix_errors` suite.
*   **Success Metric:** Pass rate > 50% (recovering the "hinted" performance without using cheats).

### Step 3: Performance Comparison
Compare token counts and logic accuracy between:
1.  **Baseline ReAct** (Exp 16): Pure discovery, no stats.
2.  **Statistical ReAct** (Exp 20): Discovery guided by usage weights.

## 4. Long-term Improvements
*   **Injectable Strategies:** Finalize the `FilteringStrategy` (TokenBudget vs Threshold) to allow the agent to request "Exhaustive" detail only when "Standard" fails.
*   **Linter Tooling:** Integrate a static analysis tool (`mypy` or `ruff`) into the implementation loop to catch Pydantic errors before execution.
