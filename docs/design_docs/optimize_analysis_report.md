# Design Doc: Optimization of Benchmark Analysis Report Generation

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
The current `generate_benchmark_report.py` (now `generate_ai_report.py`) process can be slow, especially for large benchmark runs with many failures. The "Map-Reduce" strategy for forensic analysis involves numerous LLM calls (one per attempt, then per case, then per generator). 

**Bottlenecks:**
- **Latency:** Sequential or semi-parallel LLM calls.
- **Quota:** Hitting API rate limits with high concurrency.
- **Redundancy:** Re-analyzing unchanged cases in repeated runs.

## 2. Goals
- Reduce end-to-end report generation time by 50%.
- minimize API cost and quota usage.
- Improve caching and incremental analysis.

## 3. Proposed Solutions

### A. Incremental Analysis (Caching)
**Strategy:**
- Hash the `trace_logs` and `error_message` for each attempt.
- Store the `ForensicInsight` in a persistent database (SQLite or simple JSON cache) keyed by this hash.
- Before calling the LLM, check the cache.
- **Impact:** Instant analysis for repeated failures (common in regression testing).

### B. Adaptive Concurrency Control
**Strategy:**
- Instead of a fixed Semaphore(10), implement a dynamic throttler that respects the 429 Retry-After headers globally.
- Group requests by "complexity" (token count) to pack them efficiently if using batch APIs (future).

### C. Hierarchical Summarization (Tree Reduction)
**Strategy:**
- Instead of Map (Attempt) -> Reduce (Case) -> Reduce (Generator), skip the Attempt level for "simple" errors.
- **Heuristic:** If the error is a known pattern (regex match on `ModuleNotFoundError`, `ImportError`), generate a static insight without LLM. Only use LLM for "Logic Errors" or "Hallucinations".

### D. Profiling First
**Task:**
- Instrument `generate_benchmark_report.py` with fine-grained timers.
- Measure:
    - Time spent in `_analyze_attempt` vs `_reduce_case_insights`.
    - Time spent waiting for rate limits.
    - Time loading large JSONs.

## 4. Implementation Plan
1. **Profile:** Add `time.time()` logs around key async gathers.
2. **Cache:** Implement `AnalysisCache` class using `sqlite3`.
3. **Heuristics:** Add a `StaticAnalyzer` pass before the `LLMAnalyzer`.
4. **Refactor:** Decouple the `LogAnalyzer` into a pipeline of `[Cache -> Static -> LLM]`.
