# Progress Report: Refactoring, Fixes, and Enhancements
**Date:** January 24, 2026

This report details the changes made to address the `TODO.md` items, including the rationale behind each decision and alternative approaches considered.

## 1. Tool Logic Fix: BM25 Search Tokenization

*   **Task:** Fix `search_adk_knowledge` returning "No matches" for queries like "ToolConfig" despite the class existing.
*   **Before:** The `BM25Okapi` tokenizer split text only by whitespace. Fully Qualified Names (FQNs) like `google.adk.tools.ToolConfig` were treated as a single token. A query for "ToolConfig" (token `toolconfig`) did not match the FQN token.
*   **After:** Updated `adk_knowledge_ext/search.py` to tokenize FQNs by splitting on dots (`.`) and underscores (`_`) in addition to whitespace.
    *   *Effect:* `google.adk.tools.ToolConfig` now produces tokens: `['google', 'adk', 'tools', 'toolconfig']`.
*   **Rationale:** Users often search by class name (suffix) rather than the full path. Tokenizing the path allows standard BM25 probabilistic retrieval to match these distinct parts.
*   **Alternatives Considered:**
    *   *N-Gram Indexing:* Would capture substrings but increases index size significantly and might be noisy.
    *   *Keyword Search Only:* We already have a fallback `KeywordSearchProvider` (which worked), but the user explicitly requested fixing the `bm25` mode.

## 2. Benchmark Case Fixes (`diagnose_setup_errors_mc`)

### A. `cache_ttl_string`
*   **Before:** Question asked about initializing `ContextCacheConfig` with `ttl` (string). Answer assumed `ValidationError` for type mismatch.
*   **Analysis:** The actual field name is `ttl_seconds`. Passing `ttl` raises `ValidationError: Extra inputs are not permitted`, not a type error on the value.
*   **After:** Changed question to use `ttl_seconds`.
*   **Rationale:** To correctly test the "invalid type" validation logic (Option B), we must use the correct field name.

### B. `compaction_interval_zero`
*   **Before:** Question claimed `compaction_interval=0` raises a `ValidationError`.
*   **Analysis:** Reproduction script proved that Pydantic (default integer validator) accepts `0` as a valid integer. No explicit `ge=1` validator exists in the ADK code for this field.
*   **After:** Changed Correct Answer to **D: No error**.
*   **Rationale:** The benchmark must reflect the actual runtime behavior of the code, not the "logical" expectation (unless the code is buggy, in which case the code should be fixed, but here we are testing knowledge of the current state).

### C. `sequential_empty_subagents`
*   **Before:** Question asked what happens if initialized "without sub_agents".
*   **After:** Clarified wording to "without providing the `sub_agents` argument".
*   **Rationale:** Removed ambiguity between passing `None` (potentially error) vs omitting the argument (defaults to empty list, valid).

## 3. Viewer Enhancements (`benchmark_viewer.py`)

*   **Task:** Consolidate error tabs and improve run selection visibility.
*   **Before:**
    *   Separate "Generation Error" and "Validation Error" tabs. Users had to check both.
    *   "Select Run" dropdown only showed the directory ID (timestamp), making it hard to find completed runs.
*   **After:**
    *   **Consolidated Tab:** New "Errors" tab shows both Generation errors (crash) and Validation errors (wrong answer) in one view.
    *   **Status Indicators:** The dropdown now checks for `results.json` or `trace.yaml` to display icons:
        *   ✅ `Completed`
        *   ⚠️ `Pending/Failed`
        *   ⚪ `Empty`
*   **Rationale:** Improves UX efficiency. Users can instantly see the state of a run and find the failure reason in a single location.

## 4. Tools Directory Reorganization

*   **Task:** Disambiguate forensic report scripts.
*   **Before:** `audit_failures.py` existed alongside `generate_benchmark_report.py`. The naming was unclear (Audit vs Generate vs Forensic).
*   **After:**
    *   Renamed `audit_failures.py` -> `generate_static_report.py`.
    *   Kept `generate_benchmark_report.py` (The AI-driven analyzer).
    *   Deleted `debugging.py` (Redundant functionality).
*   **Rationale:** `generate_static_report` clearly indicates it runs locally without LLM calls, distinguishing it from the AI version.

## 5. Documentation & Features

*   **Task:** Create Design Docs and implement prioritized features.
*   **Output:** Created 5 documents in `docs/design_docs/`.
*   **Implementation:** Implemented **Robust LLM-Based JSON Extraction** (`benchmarks/parsing/json_sanitizer.py`).
    *   **Architecture:** Validation Phase Sanitization (Runner-side).
    *   **Logic:** Multi-stage fallback (Direct -> Regex -> LLM Repair).
    *   **Model:** Uses `gemini-3-pro-preview` for high-fidelity extraction.

## 6. Verification & Regression Testing

To prevent future regressions of these fixes, the following permanent unit tests have been added and verified:

### A. Search Logic (`tools/adk-knowledge-ext/tests/test_search_repro.py`)
*   **Target:** `BM25SearchProvider` tokenization & Hybrid Fallback.
*   **Test Case:** Searches for a class name suffix (e.g., `ToolConfig`) and verifies that it successfully matches an FQN. Verified cascading fallback from BM25 to Keyword search.
*   **Verification:** Confirmed that splitting on dots/underscores correctly exposes the class name as a separate token for BM25, and that the Hybrid provider correctly switches strategies when needed.

### B. Benchmark Reality (`benchmarks/tests/unit/test_benchmark_definitions_reality.py`)
*   **Target:** `diagnose_setup_errors_mc` consistency.
*   **Test Cases:**
    *   `test_reality_cache_ttl_seconds_validation`: Confirms `ttl_seconds` is the valid field.
    *   `test_reality_compaction_interval_zero_allowed`: Confirms `compaction_interval=0` is allowed.
    *   `test_reality_sequential_empty_subagents`: Confirms empty sub-agents list is valid.

### C. Viewer Logic (`tools/test_benchmark_viewer.py`)
*   **Target:** Run status detection.
*   **Verification:** Verified status icon logic with mocked filesystem.

### D. JSON Sanitizer (`benchmarks/tests/unit/test_json_sanitizer.py`, `integration/test_json_formatting.py`)
*   **Target:** Output extraction robustness.
*   **Unit Tests:** Verified extraction from plain JSON, Markdown blocks, and simulated LLM repair calls.
*   **Integration Test:** `test_json_sanitizer_integration` simulates a generator returning malformed text and asserts that the `BenchmarkRunner` successfully repairs and validates it using the sanitizer.

---
**Status:** All tasks in the active batch are complete. The `TODO.md` has been updated and all regression tests are passing.
