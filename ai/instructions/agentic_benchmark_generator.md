# Agentic Benchmark Generator Development Log

## 1. Overview & Objectives
**Goal:** Implement a fully compliant **Agentic Evaluation** architecture for repository-specific benchmarking using the ADK framework.
**Context:** Static evaluation sets become stale; Agentic generates dynamic, execution-verified benchmarks that target complex, uncovered logic in a target repository (specifically `adk-python`).

**Constraints & Requirements:**
*   **Zero-Knowledge Rule:** The generator agents must not rely on pre-injected knowledge of the target repository. They must discover the topology and APIs dynamically using tools (`scan_repository`, `read_file`).
*   **Closed-Loop:** Iterative refinement of distractors via a Referee feedback turn.
*   **Zero-Trust Truth:** All correct answers must be verified by actual code execution (Golden Snapshot).
*   **Adversarial:** Distractors must be hard negatives (syntactically valid but logically flawed).

## 2. Strategic Architecture

### Design Philosophy
*   **High-Signal Targeting**: Prioritize code that is complex, uncovered, and highly relevant to the core API surface.
*   **Iterative Coverage Maximization**: Dynamically select the next target based on the maximum potential coverage lift, accounting for what has already been generated.
*   **Indisputable Ground Truth**: Trust the interpreter, not the model's prediction of output.
*   **Closed-Loop Reliability**: Self-correcting agents (Saboteur/Referee loop) to minimize human-in-the-loop overhead.

### Core Components (Agent Architecture)
*   **Topology**: **Hierarchical/Orchestrated MAS**. A `AgenticRunner` orchestrates specialized agents and workers.
*   **Discovery Strategy**: **Automated Cartography**. AST-based mapping of structure and usage.
*   **Prioritization Engine**: 
    *   **Relevancy**: Prioritizes targets that co-occur with major root nodes (e.g., `Agent`, `BaseTool`).
    *   **Coverage Lift**: Iteratively determines the updated coverage of generated benchmarks and selects the target offering the highest marginal coverage gain.
*   **Task Management**: Uses a **Task Queue** where prioritized targets are stored, allowing workers to pull and process them concurrently.
*   **Memory Model**: **State-Driven (Write-Ahead Log)**. Agents share state via a persistent `SqliteSessionService` backed by a JSONL write-ahead log.
*   **Verification**: **Adversarial Loop**. `Saboteur` proposes distractors, and the `Referee` validates them in a sandbox.

## 3. Methodology & Verification Protocol
**CRITICAL:** Every verification step MUST include the exact shell command required to execute it. 
**Strict Protocol:** Run verification after every significant architectural change.

### Verification Steps

**Step A: Unit Testing**
```bash
# MANDATORY: Verify component logic (Scanner, Tracer, Sandbox)
env/bin/python -m pytest benchmarks/benchmark_generator/test_agentic.py benchmarks/benchmark_generator/test_resumption.py benchmarks/benchmark_generator/test_key_rotation.py
```

**Step B: End-to-End Trial**
```bash
# MANDATORY: Execute the generator on the target repo
PYTHONPATH=. env/bin/python benchmarks/benchmark_generator/run_generator.py \
    --type agentic_adk \
    --repo-path ../adk-python \
    --output-dir benchmarks/benchmark_definitions/agentic_generated \
    --model gemini-3-pro-preview \
    --concurrency 1
```

**Step C: Success Criteria**
*   [x] Cartographer maps hierarchies and dependencies correctly.
*   [x] 429 errors trigger automatic key rotation and retries.
*   [x] Resumption works after simulated crash.

## 4. Running Log of Experiments
**Instruction:** Follow this cycle for every experiment:
1.  **Hypothesis:** Define what you expect to happen.
2.  **Implementation:** Make the minimal necessary change.
3.  **Verification:** Run the *exact* command from Section 3.
4.  **Analysis:** If it failed, *why*? (Check logs/traces).
5.  **Pivot:** Decide the next step (Fix, Revert, or New Strategy).

### Phase 1: Infrastructure & State Management (Attempts 1-10)
*   **Hypothesis:** A standard `InMemorySessionService` is insufficient for long-running, multi-turn generation tasks that require crash recovery.
*   **Configuration:** Refactored to use `SqliteSessionService` and `Runner` architecture.
*   **Command:** `PYTHONPATH=. env/bin/python benchmarks/benchmark_generator/run_generator.py ...`
*   **Result:** **Pass (Final)**
*   **Trace Analysis (The "Why"):**
    *   *Failures:* Initial attempts lost state updates because list mutations in session state weren't triggering SQLite writes.
    *   *Successes:* Implemented a JSONL "Write-Ahead Log" to shadow the database, ensuring perfect state persistence and enabling resumption from the exact failed turn.

### Phase 2: Topology & Prioritization (Attempt 13)
*   **Hypothesis:** Random sampling of files yields low-value benchmarks (getters/setters). AST-based complexity scoring will find "meaty" logic.
*   **Configuration:** Upgraded `scan_repository` to map Class Hierarchies and integrated `IRTManager`.
*   **Command:** Included `--irt-file` and `--coverage-file`.
*   **Result:** **Success**
*   **Trace Analysis:** The `Auditor` successfully ignored 50+ trivial files and selected `AdkWebServer` (complexity score 550), proving the "High-Signal Targeting" strategy works.

### Phase 3: Adversarial Robustness (Attempt 14-Final)
*   **Hypothesis:** Agents will try to "cheat" by mocking complex dependencies instead of using them, creating unrealistic tests.
*   **Configuration:** Added `AdversarialLoop` and a strict "No Mocks" instruction to the `Observer` agent.
*   **Result:** **Success**
*   **Trace Analysis:** The `Observer` initially failed when trying to import `unittest.mock`. After the instruction update, it correctly instantiated concrete classes, proving the "Zero-Trust Truth" constraint requires explicit enforcement.

### Phase 4: Iterative Prioritization & Task Queue (Current)
*   **Hypothesis:** Static prioritization fails to maximize coverage efficiently. Dynamic "Coverage Lift" calculation and Relevancy scoring will produce higher-value benchmarks faster.
*   **Configuration:**
    *   Updated `list_prioritized_targets` to calculate score = `Usage + Relevancy + CoverageLift`.
    *   Implemented file-backed persistence (`scanned_targets.json`) in `scan_repository` to enable "Worker Pull" architecture.
*   **Result:** **Unit Tests Passed**
*   **RCA:** N/A

### Phase 6: BFS Prioritization & Enhanced Conceptual Pipeline (Current)
*   **Hypothesis:** Relying on simple complexity scores or IRT misses critical dependencies and core infrastructure. A usage-driven BFS approach will ensure foundational components are tested first. Also, the conceptual pipeline needs deduplication to prevent semantic collisions.
*   **Configuration:**
    *   **BFS Strategy:** Implemented `list_prioritized_targets` with a stateful queue generation: `Seeds (High Usage) -> Dependencies (BFS) -> Orphans (Unused Public Entities)`.
    *   **Pipeline Upgrade:** Added the `Critic` agent to the `ConceptWorker` pipeline to enforce uniqueness using Jaccard similarity.
    *   **Tracing:** Added `generation_trace.yaml` logging to capture queue state and decision logic for debugging.
    *   **Robustness:** Refactored `save_benchmark_case` to handle flexible input types (dict/str) and prevent partial writes.
*   **Result:** **Success**
*   **Trace Analysis:**
    *   *Queue Logic:* Verified via `generation_trace.yaml` that the system correctly expanded from 11 seeds to 192 dependencies before processing orphans.
    *   *Target Selection:* High-value targets like `Runner`, `AgentTool`, and `LlmResponse` were prioritized immediately due to their high usage scores.
    *   *Resumption:* Confirmed that the BFS queue persists in the SQLite DB, allowing seamless restart without re-computation.

--- 

## 5. Critical Reflections & Lessons Learned
*   **Successes:** The "Write-Ahead Log" (JSONL) solved session persistence quirks where in-place list mutations weren't committed to SQLite. The BFS strategy successfully identified "deep" dependencies that simple random sampling missed.
*   **Failures:** Early attempts to use `MagicMock` in the Truth Lab crashed Pydantic-based code in the target repo. The `Assembler` initially hallucinated function names (e.g., `forecast_timesfm`) by conflating code symbols; strict prompt instructions fixed this.
*   **Insights:** Structured output (`output_schema`) combined with strict tool-calling instructions is the only way to get reliable multi-agent orchestration from current model generations.

## 6. Usage & Artifacts
**File Structure:**
*   `agents.py`: MAS orchestration logic (Sequential, Loop, Specialized).
*   `tools.py`: AST Scanner, BFS Strategist, Truth Lab, and Sandbox.
*   `logger.py`: Colored console logger and structured file tracer.
*   `run_generator.py`: CLI entry point.

**Final Execution Command:**
```bash
PYTHONPATH=. env/bin/python benchmarks/benchmark_generator/run_generator.py \
    --type agentic_adk \
    --output-dir benchmarks/benchmark_definitions/agentic_generated \
    --model-name gemini-3-pro-preview \
    --repo-path ../adk-python \
    --concurrency 2 \
    --session-db agentic_sessions.db \
    --mode concept_mcq
```

## 7. Appendix: Comprehensive Experiment Log

| ID | Experiment Name | Command / Config | Result | Key Finding |
| :--- | :--- | :--- | :--- | :--- |
| **Exp 1-10** | Infrastructure & State | `python run_generator.py` | **Pass** (Eventually) | `InMemorySessionService` state deltas must be initialized via `runner.run_async(state_delta=...)` to persist correctly. |
| **Exp 11** | Topology Mapping | `scan_repository` tool | **Pass** | AST-based `Cartographer` successfully identified complex targets like `AdkWebServer`. |
| **Exp 12** | Rate Limiting (429) | `SemaphoreGemini` + `ApiKeyManager` | **Pass** | Standard ADK `RotatingKeyGemini` needs a manual retry loop to handle `429` effectively during a stream. |
| **Exp 13** | Coverage Logic | `--coverage-file` | **Pass** | Coverage penalties (`-50` score) successfully steered the `Auditor` to uncovered files. |
| **Exp 14** | End-to-End Validation | Full Loop (`gemini-2.0-flash-exp`) | **Pass** | The "No Mocks" strict instruction is critical; `MagicMock` crashes Pydantic models in the target repo. |
