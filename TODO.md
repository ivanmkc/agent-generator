# Todo List
TODO

# On Hold (do not start)
## 1. Vector Search for Ranked Targets (`ai/instructions/design_docs/mcp_server/vector_search_ranked_targets.md`)
- [x] **Implementation:**
    - [x] Create `tools/build_vector_index.py` to embed `ranked_targets.yaml`.
    - [x] Implement `VectorSearchProvider` in `AdkTools`.
    - [x] Integrate into `search_ranked_targets` (Hybrid BM25 + Vector).
- [x] **Verification:**
    - [x] Add `benchmark_definitions/search_relevance` to test semantic queries.

## 2. Synthetic Retrieval Dataset (`ai/instructions/design_docs/synthetic_retrieval_dataset.md`)
- [ ] **Verification:**
    - [ ] Run the whole pipeline again on the latest dataset and ensure convergence works as expected.

## 3. Question Quality Verifier (`ai/instructions/design_docs/question_quality_verifier.md`)
- [ ] **Implementation:**
    - [ ] Create `tools/verify_benchmarks.py` script.
    - [ ] Implement `VerifierAgent` using `AdkAnswerGenerator`.
    - [ ] Create a loop to run verification on all cases in `benchmarks/benchmark_definitions`.
    - [ ] Generate `quality_report.md`.

## 4. MCP Update Command (`ai/instructions/design_docs/mcp_server/mcp_update_command.md`)
- [ ] **Implementation:**
    - [ ] Add `mcp update` command to `manage_mcp.py`.
    - [ ] Implement git synchronization logic to pull latest changes for cached repositories.
    - [ ] Add index refresh logic.

## Codebase Agnosticism
- [ ] **Agnostic Verification:** Add benchmark tests to ensure that when analyzing non-ADK-python codebases, the agent does NOT rely on or attempt to use ADK-specific tools (like `run_adk_agent`).
- [ ] **Registry Expansion:** Add more common open-source repositories to `registry.yaml` to verify the zero-config workflow at scale.
- [ ] Seems like ranked targets doesn't include detailed info about how to reference artifacts in instructions. This info might be missing from docstrings. Create a design doc for a pipeline to generate relevant docstrings that cover functional information not covered in the API reference.
- [ ] Rename adk_knowledge_ext to something more fitting

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
- [ ] **Index Automation:** Create a script to rebuild `ranked_targets.yaml` for the latest `adk-python` release and update the registry.
- [ ] **Registry Automation:** Implement `tools/manage_registry.py` based on `ai/instructions/design_docs/mcp_server/registry_architecture.md`.


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

## 0. MCP Server Implementation (Ranked Knowledge) [COMPLETED]
- [x] **Implementation:**
    - [x] Formalize the `adk-knowledge-mcp` server used by `mcp_adk_agent_runner_ranked_knowledge`.
    - [x] Expose specialized tools: `list_modules`, `inspect_symbol`, `read_source_code`, and `search_knowledge`.
    - [x] Ensure the server uses the `ranked_targets.yaml` index and supports hybrid (BM25 + Vector) search.
    - [x] Support automatic repository cloning and index downloading via an internal registry.
- [x] **Verification:**
    - [x] Create comprehensive integration test suite for multiple installation and configuration scenarios.
    - [x] Verify end-to-end functionality using the `mcp_codebase_knowledge_runner` in benchmarks.

## 4. MCP Update Command (Design Doc)
- [x] **Design:** Created proposal `ai/instructions/design_docs/mcp_server/mcp_update_command.md`.
- [ ] **Implementation:** On Hold.
