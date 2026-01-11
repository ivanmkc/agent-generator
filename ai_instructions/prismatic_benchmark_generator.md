# Prismatic Benchmark Generator Development Log

## 1. Overview & Objectives
**Goal:** Implement a fully compliant **Prismatic Evaluation** architecture for repository-specific benchmarking using the ADK framework.
**Context:** Static evaluation sets become stale; Prismatic generates dynamic, execution-verified benchmarks that target complex, uncovered logic in a target repository (specifically `adk-python`).

**Constraints & Requirements:**
*   **Zero-Knowledge Rule:** The generator agents must not rely on pre-injected knowledge of the target repository. They must discover the topology and APIs dynamically using tools (`scan_repository`, `read_file`).
*   **Closed-Loop:** Iterative refinement of distractors via a Referee feedback turn.
*   **Zero-Trust Truth:** All correct answers must be verified by actual code execution (Golden Snapshot).
*   **Adversarial:** Distractors must be hard negatives (syntactically valid but logically flawed).

## 2. Strategic Architecture

### Design Philosophy
*   **High-Signal Targeting:** Prioritize code that is complex and uncovered (Fisher Information maximization).
*   **Indisputable Ground Truth:** Trust the interpreter, not the model's prediction of output.
*   **Closed-Loop Reliability:** Self-correcting agents (Saboteur/Referee loop) to minimize human-in-the-loop overhead.

### Core Components (Agent Architecture)
*   **Topology:** **Hierarchical/Orchestrated MAS.** A `PrismaticRunner` orchestrates a team of specialized agents (`Auditor`, `Observer`, `Saboteur`).
*   **Discovery Strategy:** **Automated Cartography.** The `Auditor` agent uses a specialized `scan_repository` tool (AST-based) to map the codebase structure and usage statistics without reading full file contents.
*   **Memory Model:** **State-Driven (Write-Ahead Log).** Agents share state via a persistent `SqliteSessionService` backed by a JSONL write-ahead log to survive crashes and support resumption.
*   **Verification:** **Adversarial Loop.** The `Saboteur` proposes distractors, and the `Referee` (Sandbox) attempts to execute them to prove they are "hard negatives" (plausible but incorrect).

## 3. Methodology & Verification Protocol
**CRITICAL:** Every verification step MUST include the exact shell command required to execute it. 
**Strict Protocol:** Run verification after every significant architectural change.

### Verification Steps

**Step A: Unit Testing**
```bash
# MANDATORY: Verify component logic (Scanner, Tracer, Sandbox)
env/bin/python -m pytest benchmarks/benchmark_generator/test_prismatic.py benchmarks/benchmark_generator/test_resumption.py benchmarks/benchmark_generator/test_key_rotation.py
```

**Step B: End-to-End Trial**
```bash
# MANDATORY: Execute the generator on the target repo
PYTHONPATH=. env/bin/python benchmarks/benchmark_generator/run_generator.py \
    --type prismatic_adk \
    --repo-path ../adk-python \
    --output-dir benchmarks/benchmark_definitions/prismatic_generated \
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

--- 

## 5. Critical Reflections & Lessons Learned
*   **Successes:** The "Write-Ahead Log" (JSONL) solved session persistence quirks where in-place list mutations weren't committed to SQLite.
*   **Failures:** Early attempts to use `MagicMock` in the Truth Lab crashed Pydantic-based code in the target repo.
*   **Insights:** Structured output (`output_schema`) combined with strict tool-calling instructions is the only way to get reliable multi-agent orchestration from current model generations.

## 6. Usage & Artifacts
**File Structure:**
*   `agents.py`: MAS orchestration logic.
*   `tools.py`: AST Scanner, Tracer, and Sandbox.
*   `irt.py`: IRT-based prioritization scoring.
*   `run_generator.py`: CLI entry point.

**Final Execution Command:**
```bash
PYTHONPATH=. env/bin/python benchmarks/benchmark_generator/run_generator.py \
    --type prismatic_adk \
    --output-dir benchmarks/benchmark_definitions/prismatic_generated \
    --model gemini-3-pro-preview \
    --repo-path ../adk-python \
    --concurrency 1 \
    --session-db prismatic_sessions.db
```

## 7. Appendix: Comprehensive Experiment Log

| ID | Experiment Name | Command / Config | Result | Key Finding |
| :--- | :--- | :--- | :--- | :--- |
| **Exp 1-10** | Infrastructure & State | `python run_generator.py` | **Pass** (Eventually) | `InMemorySessionService` state deltas must be initialized via `runner.run_async(state_delta=...)` to persist correctly. |
| **Exp 11** | Topology Mapping | `scan_repository` tool | **Pass** | AST-based `Cartographer` successfully identified complex targets like `AdkWebServer`. |
| **Exp 12** | Rate Limiting (429) | `SemaphoreGemini` + `ApiKeyManager` | **Pass** | Standard ADK `RotatingKeyGemini` needs a manual retry loop to handle `429` effectively during a stream. |
| **Exp 13** | Coverage Logic | `--coverage-file` | **Pass** | Coverage penalties (`-50` score) successfully steered the `Auditor` to uncovered files. |
| **Exp 14** | End-to-End Validation | Full Loop (`gemini-2.0-flash-exp`) | **Pass** | The "No Mocks" strict instruction is critical; `MagicMock` crashes Pydantic models in the target repo. |
