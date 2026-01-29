# Todo List

# Immediate Priorities (Refactoring Phase 2)

## 1. Codebase Improvements
- [x] **Refactor ModelName:** Move the `ModelName` enum to `core/models.py` (or `core/constants.py`) so both `benchmarks` and `config` can import it without circular dependency.
- [x] **Consolidate Data Paths:** Review `core/config.py` paths (`AGENTIC_SESSIONS_DB`, `VIBESHARE_RESULTS_FILE`, etc.). Simplify by moving all runtime state to a unified `data/` directory or a single SQLite database (`core.db`). Remove ad-hoc JSONL/YAML files where possible.
- [x] **Adopt Pydantic Settings:** Upgrade `core/config.py` to use `pydantic-settings`. This allows robust environment variable overrides (e.g., `ADK_OUTPUT_ROOT=/tmp/custom`) which is crucial for CI/CD flexibility.
- [x] **Remove `utils.py` Anti-Pattern:** Decompose `core/utils.py` (if/when created) into semantic modules like `core/filesystem.py`, `core/strings.py`, etc.
- [x] **Refactor Answer Generators:** Moved `experiment_66/67` back to `experiments/` and fixed imports in `benchmarks/` to restore modularity.
- [x] **Vibeshare Independence:** Ensure `vibeshare/` treats the main repo as a proper library dependency rather than using cross-imports. Audit `vibeshare/src/cache.py` vs `core/config.py` usage.
- [x] **FunctionTool Signature:** Fixed `ranked_targets.yaml` generation to include `FunctionTool` constructor signature (regenerated file).
- [x] **Delete Error 24:** Removed `fix_errors:24_incorrect_api_usage` as it was badly designed.

# Ongoing Maintenance

## Benchmark Case Reviews & Fixes
- [ ] **Predict Runtime Behavior Review:** `predict_runtime_behaviour` cases with `code_snippet_ref` need manual review for validity.
- [x] **Duplicate Name Check:** Verified `predict_runtime_behavior_mc:duplicate_agent_name` matches `validate_sub_agents_unique_names` behavior (warning logged, no error raised).
- [x] **Event Extra Fields:** Verified `predict_runtime_behavior_mc:event_extra_fields_error` matches code (Pydantic forbids extra fields).
- [x] **Tool Injection Ambiguity:** Improved `predict_runtime_behavior_mc:tool_session_id_injection` by clarifying options and explanation.
- [x] **Custom Agent Sub-agents:** Enforced strict `sub_agents` registration in `fix_errors:08_custom_agent` by updating the test assertions.

## Codebase Maintenance
- [ ] **Notebook CI:** Add a CI step (or pre-commit hook) to run `papermill` on visualization notebooks with dummy data to prevent regressions.
- [ ] **Canonical Agent:** Create one canonical agent that uses 99% of the API, with comments. This will be used as a sample to present as initial context. It needs tests.
- [x] **List Modules Pagination:** Determined that Page 1 (first 51 items) captures >99% of cumulative usage (368/370).

# On Hold (do not start)

## 1. Generate a notebook that analyzes the percentage cumulative usage of ranked_targets.yaml. I want to know how many items to return on first page which will capture (>99% of usage).

## 2. Vector Search for Ranked Targets (`docs/design_docs/vector_search_ranked_targets.md`)
- [x] **Implementation:**
    - [x] Create `tools/build_vector_index.py` to embed `ranked_targets.yaml`.
    - [x] Implement `VectorSearchProvider` in `AdkTools`.
    - [x] Integrate into `search_ranked_targets` (Hybrid BM25 + Vector).
- [x] **Verification:**
    - [x] Add `benchmark_definitions/search_relevance` to test semantic queries.

## 3. Synthetic Retrieval Dataset (`docs/design_docs/synthetic_retrieval_dataset.md`)
- [ ] **Verification:**
    - [ ] Run the whole pipeline again on the latest dataset and ensure convergence works as expected.

## 4. Question Quality Verifier (`docs/design_docs/question_quality_verifier.md`)
- [ ] **Implementation:**
    - [ ] Create `tools/verify_benchmarks.py` script.
    - [ ] Implement `VerifierAgent` using `AdkAnswerGenerator`.
    - [ ] Create a loop to run verification on all cases in `benchmarks/benchmark_definitions`.
    - [ ] Generate `quality_report.md`.

# Completed

## Refactoring & Core
- [x] **Core Module:** Created `core/` with `config.py`, `models.py`, and `logging_utils.py`.
- [x] **Directory Structure:** Moved `tools/benchmark_generator` to `benchmarks/generator`, moved experiments to `experiments/`, deleted redundant `docs/`.
- [x] **Cleanup:** Removed `tools/constants.py`, `benchmarks/config.py`, and redundant notebooks/scripts.
- [x] **Notebooks:** Renamed analysis notebooks to be descriptive (`forensic_failure_analysis.ipynb`) and parameterized for Papermill.
- [x] **Documentation:** Added module-level docstrings across the codebase.
- [x] **ModelName:** Moved `ModelName` to `core/models.py`.
- [x] **Data Paths:** Consolidated paths to `data/` directory.
- [x] **Pydantic Settings:** Implemented env var reading for config (using `os.environ` as lightweight alternative).
- [x] **Trace Utils:** Moved trace utilities to `core/trace_utils.py` and deleted `benchmarks/utils.py`.

## Features
- [x] **Implement Robust LLM-Based JSON Extraction:** Created `JsonSanitizer` with multi-stage fallback (Direct -> Regex -> LLM Repair) and integrated it into `BenchmarkRunner`.
- [x] **Missing signatures:** Added `signature` field to `RankedTarget` model and populated it.
- [x] **Synthetic Retrieval Dataset:** Implemented randomization, removed manual retry, added refusal reason, suppressed AFC logs, added convergence logging, zero-context baseline checks, and resumption support.

## Fixes
- [x] **Fix Ambiguous Runner Question:** Reworded `api_understanding` questions.
- [x] **Observer Plugin Ambiguity:** Reworded `api_understanding` questions.
- [x] **Custom Tool Implementation:** Fixed `configure_adk_features_mc` case.
- [x] **Fix BM25 Search:** Updated tokenization.
- [x] **Search Fallback:** Implemented cascading fallback.
- [x] **Search Determinism:** Added stable sorting.
- [x] **Benchmark Reality Checks:** Fixed multiple reality check benchmarks.
- [x] **Viewer:** Consolidated error tabs and added run status indicators.
- [x] **Tools:** Reorganized `tools/cli`.
- [x] **Hybrid Generator:** Fixed `create_hybrid_generator_v47` integration.