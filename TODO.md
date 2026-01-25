# Todo List

# Prioritized Features (From Design Docs)

## 1. Implement Search Suggestions (`docs/design_docs/search_suggestions.md`)
- [ ] **Implementation:**
    - [ ] Add `difflib` or `rapidfuzz` dependency if needed (or use stdlib `difflib`).
    - [ ] Create `SimilaritySearchProvider` or update `AdkTools` to handle fuzzy matching.
    - [ ] Update `search_ranked_targets` to trigger suggestion logic when `results` is empty.
    - [ ] Format output to include "Did you mean?" section with scores.
- [ ] **Verification:**
    - [ ] Add unit test with typo inputs (e.g., "ToolConfg") ensuring correct suggestions.

## 2. Implement Usage-Ranked Pagination (`docs/design_docs/list_modules_pagination.md`)
- [ ] **Implementation:**
    - [ ] Modify `AdkTools.list_ranked_targets` to accept a sorting strategy (defaulting to 'usage').
    - [ ] Ensure `ranked_targets.yaml` is loaded and items have `usage_score` populated (already done in `RankedTarget` model).
    - [ ] Update default sort order to `(-usage_score, id)`.
- [ ] **Verification:**
    - [ ] Unit test ensuring high-usage classes (e.g., `LlmAgent`) appear on Page 1.

## 3. Optimize Analysis Report Generation (`docs/design_docs/optimize_analysis_report.md`)
- [ ] **Implementation:**
    - [ ] Implement `AnalysisCache` (JSON/SQLite) to store `ForensicInsight` by trace hash.
    - [ ] Update `LogAnalyzer` to check cache before calling LLM.
    - [ ] Implement adaptive concurrency/throttling for API calls.
- [ ] **Verification:**
    - [ ] Benchmark report generation time on a repeated run (should be near-instant).

## 4. Question Quality Verifier (`docs/design_docs/question_quality_verifier.md`)
- [ ] **Implementation:**
    - [ ] Create `tools/verify_benchmarks.py` script.
    - [ ] Implement `VerifierAgent` using `AdkAnswerGenerator`.
    - [ ] Create a loop to run verification on all cases in `benchmarks/benchmark_definitions`.
    - [ ] Generate `quality_report.md`.

# Active Legacy Tasks

## Benchmark Case Reviews & Fixes
- [ ] **Fix Ambiguous Runner Question:** `api_understanding:which_class_is_used_to_run_multiple_agents_concurr` is ambiguous as `Runner` can run multiple agents via `run_async`.
    - *Action:* Reword to be explicit about "parallel execution class" vs "runner".
- [ ] **Predict Runtime Behavior Review:** `predict_runtime_behaviour` cases with `code_snippet_ref` need manual review for validity.
- [ ] **Duplicate Name Check:** Verify `predict_runtime_behavior_mc:duplicate_agent_name` matches `validate_sub_agents_unique_names` behavior (warning vs error).
- [ ] **Event Extra Fields:** Verify `predict_runtime_behavior_mc:event_extra_fields_error`.
- [ ] **Tool Injection Ambiguity:** Improve `predict_runtime_behavior_mc:tool_session_id_injection`.
- [ ] **Observer Plugin Ambiguity:** `api_understanding:which_specific_plugin_class_is_designed_to_observe` might be satisfied by `BigQueryAgentAnalyticsPlugin`. Reword to be specific.
- [ ] **Custom Tool Implementation:** `configure_adk_features_mc:you_are_implementing_a_custom_tool_which_method_mu` is likely wrongly answered. Check code, write test, fix.
- [ ] **Custom Agent Sub-agents:** Check if `fix_errors:08_custom_agent` needs `sub_agents` passed to `CustomConditionalAgent`.

## Codebase Maintenance
- [ ] **Canonical Agent:** Create one canonical agent that uses 99% of the API, with comments.
- [ ] **List Modules Pagination:** Determine at what page cumulative usage hits 99%.

# Completed

## Features
- [x] **Implement Robust LLM-Based JSON Extraction:** Created `JsonSanitizer` with multi-stage fallback (Direct -> Regex -> LLM Repair) and integrated it into `BenchmarkRunner`.

## Fixes
- [x] **Fix BM25 Search:** Updated tokenization to split FQNs by dots/underscores.
- [x] **Search Fallback:** Implemented cascading fallback from BM25 to Keyword search in `HybridSearchProvider`.
- [x] **Search Determinism:** Added stable sorting to search providers.
- [x] **Benchmark Reality Checks:** Fixed `cache_ttl_string` (ttl_seconds), `compaction_interval_zero` (no error), and `sequential_empty_subagents` questions.
- [x] **Viewer:** Consolidated error tabs and added run status indicators.
- [x] **Tools:** Reorganized `tools/cli` and renamed `audit_failures.py`.
- [x] **Hybrid Generator:** Fixed `create_hybrid_generator_v47` integration.