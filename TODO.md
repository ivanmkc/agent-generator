# Todo List

# Prioritized Features (From Design Docs)

## 1. Generate a notebook that analyzes the percentage cumulative usage of ranked_targets.yaml. I want to know how many items to return on first page which will capture (>99% of usage).

## 2. Question Quality Verifier (`docs/design_docs/question_quality_verifier.md`)
- [ ] **Implementation:**
    - [ ] Create `tools/verify_benchmarks.py` script.
    - [ ] Implement `VerifierAgent` using `AdkAnswerGenerator`.
    - [ ] Create a loop to run verification on all cases in `benchmarks/benchmark_definitions`.
    - [ ] Generate `quality_report.md`.

# Active Legacy Tasks

## Benchmark Case Reviews & Fixes
- [ ] **Predict Runtime Behavior Review:** `predict_runtime_behaviour` cases with `code_snippet_ref` need manual review for validity.
- [ ] **Duplicate Name Check:** Verify `predict_runtime_behavior_mc:duplicate_agent_name` matches `validate_sub_agents_unique_names` behavior (warning vs error).
- [ ] **Event Extra Fields:** Verify `predict_runtime_behavior_mc:event_extra_fields_error`.
- [ ] **Tool Injection Ambiguity:** Improve `predict_runtime_behavior_mc:tool_session_id_injection`.
- [ ] **Custom Agent Sub-agents:** Check if `fix_errors:08_custom_agent` needs `sub_agents` passed to `CustomConditionalAgent`.

## Codebase Maintenance
- [ ] **Canonical Agent:** Create one canonical agent that uses 99% of the API, with comments. This will be used as a sample to present as initial context. It needs tests.
- [ ] **List Modules Pagination:** Determine at what page cumulative usage hits 99%.

# Completed

## Features
- [x] **Implement Robust LLM-Based JSON Extraction:** Created `JsonSanitizer` with multi-stage fallback (Direct -> Regex -> LLM Repair) and integrated it into `BenchmarkRunner`.

## Fixes
- [x] **Fix Ambiguous Runner Question:** Reworded `api_understanding:which_class_is_used_to_run_multiple_agents_concurr` to specify "sub-agents" and point to `ParallelAgent`.
- [x] **Observer Plugin Ambiguity:** Reworded `api_understanding:which_specific_plugin_class_is_designed_to_observe` to specify "standard logger".
- [x] **Custom Tool Implementation:** Fixed `configure_adk_features_mc:you_are_implementing_a_custom_tool_which_method_mu` to allow `run_async` as the correct answer.
- [x] **Fix BM25 Search:** Updated tokenization to split FQNs by dots/underscores.
- [x] **Search Fallback:** Implemented cascading fallback from BM25 to Keyword search in `HybridSearchProvider`.
- [x] **Search Determinism:** Added stable sorting to search providers.
- [x] **Benchmark Reality Checks:** Fixed `cache_ttl_string` (ttl_seconds), `compaction_interval_zero` (no error), and `sequential_empty_subagents` questions.
- [x] **Viewer:** Consolidated error tabs and added run status indicators.
- [x] **Tools:** Reorganized `tools/cli` and renamed `audit_failures.py`.
- [x] **Hybrid Generator:** Fixed `create_hybrid_generator_v47` integration.