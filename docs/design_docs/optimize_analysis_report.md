# Design Doc: Optimization of Benchmark Analysis Report Generation

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
The current `generate_ai_report.py` process is slow during its first (and usually only) run for a benchmark directory. The "Map-Reduce" strategy for forensic analysis involves a high volume of LLM calls that are often constrained by sequential processing, redundant context transmission, and strict rate limits.

**Bottlenecks:**
- **High Input Latency:** Sending full, uncompressed trace logs for every attempt increases model latency and token costs.
- **Quota Starvation:** Fixed concurrency often triggers 429 errors, leading to long backoff periods.
- **Hierarchical Overhead:** Waiting for all "Map" tasks (attempts) to finish before starting "Reduce" tasks (cases) creates an orchestration bottleneck.

## 2. Goals
- Reduce the time required for a first-run report by 60%.
- Minimize token usage by pruning redundant trace data.
- Improve throughput by using adaptive concurrency.

## 3. Proposed Solutions

### A. Intelligent Context Pruning (Static Slicing)
**Strategy:**
- Before calling the LLM, use a static analyzer to slice the `trace_logs`.
- Focus on events near the error timestamp or the final 5 tool calls.
- **Impact:** Reduces input tokens by 70-80%, significantly speeding up model response time.

### B. Adaptive Concurrency & Global Throttling
**Strategy:**
- Replace the fixed `asyncio.Semaphore` with an `AdaptiveThrottler`.
- Monitor response headers for `Retry-After` or `Rate-Limit` info.
- Scale concurrency up until the first warning, then back off. This maximizes throughput without hitting hard 300s penalties.

### C. Multi-Model Tiering (Flash-First)
**Strategy:**
- Use **Gemini Flash** for the "Map" stage (analyzing individual attempts). It is significantly faster and cheaper.
- Reserve **Gemini Pro** for the "Reduce" stage (synthesizing case patterns and generator forensics) where deep reasoning is required.
- **Impact:** Decreases total execution time and cost without sacrificing high-level insights.

### D. Streaming Pipeline (Early Reduction)
**Strategy:**
- Instead of waiting for *all* attempts in a case to finish, start the Case Reduction as soon as its attempts are ready.
- Implement as a graph of async tasks rather than a linear sequence of `gather()` calls.

### E. Static Heuristics (LLM-Skip)
**Strategy:**
- Identify obvious failure modes (e.g., specific Python Tracebacks, Quota errors) via regex.
- Generate a "Static Insight" instantly and skip the LLM call for that attempt.

## 4. Implementation Plan
1. **Profiling:** Add fine-grained instrumentation to identify if the bottleneck is network, model processing, or orchestration.
2. **Context Slicer:** Implement a `TraceSlicer` utility to extract relevant snippets.
3. **Adaptive Throttler:** Implement the throttler and integrate it into `LogAnalyzer`.
4. **Flash Routing:** Update `LogAnalyzer` to accept a `base_model` (Flash) and `synthesis_model` (Pro).