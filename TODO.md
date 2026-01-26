# Todo List
## 1. Missing signatures in ranked_targets.yaml for method.
- [x] Added `signature` field to `RankedTarget` model.
- [x] Updated `TargetRanker` to populate signature from `signature_full`.
- [x] Updated `test_ranked_targets.py` to assert signature presence for methods.
- [x] Regenerated `ranked_targets.yaml` with signatures.

## 2. Synthetic Retrieval Dataset (`docs/design_docs/synthetic_retrieval_dataset.md`)
- [ ] **Implementation:**
    - [x] In DataValidator._generate_candidate_pool: Randomize candidates
    - [x] In DataValidator: Remove the manual retry here since the ApiKeyManager already handles key rotation. See how benchmark_runner handles it.
    - [ ] In DataValidator._generate_answer_with_retry: Modify the data model that is returned by AnswerGenerator's to allow a refusal_reason: str, which is used to refuse answering if it doesn't know or feels unconfident to answer, based on the given context. This would count as a validation failure but as least the model can refuse to guess, which keeps data clean from random guessing.
    - [ ] Not a dealbreaker, but can you find out why the stdout includes "AFC is enabled with max remote calls: 10." and surpress it if possible?
    - [ ] I want the in-progress logging to show convergence metrics (per-context) once in a while so I can see how long convergence will take. I imagine that once a particular context has converged, it can be removed from the candidate pool to make room for other context, or at least it's pick rate can be lowered? wdyt is way to do this without introducing more hyperparameters?
    - [ ] Prompt the LLM to only answer based on info from context and not from it's own preconcieved knowledge.
    - [ ] Report should show 'Impact Scores' as order of impact (descending)
    - [ ] Increase max trials from 150 to 500
    - [ ] Plan in the design doc, an adaptive (simulated annealing type) solution to gradually lower number of context to optimize information gain (by isolating context) over time. Prove or disprove this can work mathematically. Show whether it can improve convergence rates. Do not implement.
    - [ ] Running Zero-Context Baseline: Needs to be run sufficiently long to establish confidence. Please log how many trials were used and confidence level. If baseline success rate mean is greater than would be expected from random guessing (calculate this % for MC. for non-MC the bar is that the mean must be 0.0), then skip this question.
        - [ ] In the generated report, include a section to show the skipped questions
        - [ ] In design doc, show mathematically whether these questions (that can pass with zero-context) can harm convergence times or prevent it altogether.
    - [ ] Since it's possible to run out of quota on these long generations, please add a way to continue a specific run from an arbitrary stoppage. Add an integration test for this functionality.
    - [ ] All internal functions under retrieval_dataset_generation need docstrings, methodology and explanation of how to interpret/use outputs if not immediately obvious, e.g. case.is_sufficient_set

# On Hold (do not start)

## 1. Generate a notebook that analyzes the percentage cumulative usage of ranked_targets.yaml. I want to know how many items to return on first page which will capture (>99% of usage).

## 2. Question Quality Verifier (`docs/design_docs/question_quality_verifier.md`)
- [ ] **Implementation:**
    - [ ] Create `tools/verify_benchmarks.py` script.
    - [ ] Implement `VerifierAgent` using `AdkAnswerGenerator`.
    - [ ] Create a loop to run verification on all cases in `benchmarks/benchmark_definitions`.
    - [ ] Generate `quality_report.md`.

## 3. Vector Search for Ranked Targets (`docs/design_docs/vector_search_ranked_targets.md`)
- [ ] **Implementation:**
    - [ ] Create `tools/build_vector_index.py` to embed `ranked_targets.yaml`.
    - [ ] Implement `VectorSearchProvider` in `AdkTools`.
    - [ ] Integrate into `search_ranked_targets` (Hybrid BM25 + Vector).
- [ ] **Verification:**
    - [ ] Add `benchmark_definitions/search_relevance` to test semantic queries.
    
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