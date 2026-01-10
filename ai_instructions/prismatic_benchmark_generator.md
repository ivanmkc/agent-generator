# Development Log: Prismatic Benchmark Generator

## 1. Strategic Design Goals
Beyond simply implementing the specification, this system is designed to solve specific problems in automated benchmarking:

### A. High-Signal Targeting (The "anti-bloat" principle)
*   **Problem:** Most auto-generated benchmarks test trivial code (getters, setters), inflating scores without measuring reasoning.
*   **Goal:** Maximize **Fisher Information**. We prioritize code that is complex, uncovered, and historically "discriminating" (hard for bad models, easy for good ones).
*   **Mechanism:** `Auditor` agent driven by `IRTManager` and `scan_repository` (Cyclomatic Complexity).

### B. Execution-First Truth (The "anti-hallucination" principle)
*   **Problem:** LLM-generated "correct answers" are often subtly wrong.
*   **Goal:** **Indisputable Ground Truth.** We do not trust the model's prediction of output; we trust the interpreter.
*   **Mechanism:** `Observer` generates code, but `Tracer` *executes* it to capture the Golden Snapshot. If it doesn't run, it's not a benchmark.

### C. Adversarial Hardness (The "reasoning" principle)
*   **Problem:** Multiple choice questions are often solvable by elimination or syntax checks.
*   **Goal:** **Hard Negatives.** Distractors must be syntactically valid and plausible ("Look correct") but semantically divergent. This forces the evaluated agent to trace logic, not just parse syntax.
*   **Mechanism:** `Saboteur` agent focused on specific mutation operators (Semantic, Poisoning, Structure) validated by `Referee`.

### D. Autonomy & Robustness
*   **Problem:** Human-in-the-loop generation is unscalable.
*   **Goal:** **Closed-Loop Reliability.** The system must detect its own failures (e.g., generated code doesn't import) and self-correct or skip without crashing the pipeline.
*   **Mechanism:** `PrismaticLoop` with error handling, state delta persistence, and retries.

---

## 2. Methodology & Verification

### Verification Protocol
**Step A: Unit Testing**
Run component-level tests to verify tools (Scanner, Tracer, Sandbox) and agent instantiation.
```bash
env/bin/python -m pytest benchmarks/benchmark_generator/test_prismatic.py
```

**Step B: End-to-End Trial**
Execute the generator on the `adk-python` repository.
```bash
PYTHONPATH=. env/bin/python benchmarks/benchmark_generator/run_generator.py \
    --type prismatic_adk \
    --repo-path ../adk-python \
    --output-dir benchmarks/benchmark_definitions/prismatic_generated \
    --model gemini-3-pro-preview
```

---

## 3. Running Log & Experiments

### Phase 1: Infrastructure & Compliance (Attempts 1-12)
*   **Action:** Refactored initial Python script into full ADK Multi-Agent System.
*   **Challenge:** `InMemorySessionService` state persistence and `InvocationContext` injection failures.
*   **Solution:** Implemented `Runner` with explicit `create_session` and used `state_delta` to initialize shared state for the `LlmAgent` instruction templates.
*   **Result:** **Success.** The pipeline runs, agents communicate, and state is preserved across the loop.

### Phase 2: Topology & Intelligence (Attempt 13)
*   **Action:** Upgraded `scan_repository` (Cartographer) to use `ast` for mapping Class Hierarchies and Dependency Graphs.
*   **Action:** Integrated `IRTManager` for prioritization.
*   **Result:** **Success.** The `Auditor` now intelligently selects targets like `AdkWebServer` (complexity 550) over trivial scripts.

### Phase 3: Validation Run (Attempt 14)
*   **Observation:** The generator ran a full cycle on `../adk-python`.
    *   **Auditor:** Selected `src/google/adk/cli/adk_web_server.py`.
    *   **Observer:** Generated valid-looking code but failed execution due to `ModuleNotFoundError: No module named 'src'`.
    *   **Referee:** Correctly flagged the missing snapshot.
    *   **System:** Looped back to start before hitting `429 RESOURCE_EXHAUSTED`.
*   **Design Validation:** The architecture holds. The system correctly identified a failure (missing snapshot) and didn't crash; it attempted to proceed (or would have retried/skipped).

---

## 4. Critical Reflections & Future Work

### 1. Environment Isolation vs. Convenience
**Issue:** The `trace_execution` tool runs `exec()` in the generator's process. The generated code often assumes it's running from the repo root (e.g., `from src.google...`), which fails when running from the `benchmarks/` directory without `sys.path` modification.
**Fix:** `trace_execution` needs to dynamically append `repo_path` to `sys.path` or run in a subprocess with `PYTHONPATH` set to `repo_path`.

### 2. Model Compliance
**Issue:** Even with `output_schema`, earlier model generations sometimes output conversational text instead of strict tool calls.
**Fix:** Move to `gemini-3-pro` (as configured) or use `tool_choice='required'` if supported by the ADK adapter for stricter control.

### 3. Rate Limiting
**Issue:** The multi-agent loop is extremely token-heavy (Auditor -> Observer -> Saboteur -> Referee -> Critic -> Assembler).
**Fix:**
    *   **Batching:** Have the Auditor select *N* targets at once.
    *   **Optimization:** Reduce context window for `Saboteur` (doesn't need full repo map, just the snapshot).