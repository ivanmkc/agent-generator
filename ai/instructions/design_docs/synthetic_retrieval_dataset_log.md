# Retrieval Dataset Generation

## Progress Log

### 1. Initialization
- **Task:** Create directory structure and initial scripts.
- **Result:** Created `tools/retrieval_dataset_generation/` and populated it with `extract_data.py`, `validate_data.py`, and `lib.py`.

### 2. Implementation: Phase 1 (Extractor)
- **Task:** Implement `extract_data.py` to mine benchmarks.
- **Method:** Implemented extraction logic for `api_understanding` (Answer Template mining), `fix_errors` (Import parsing), and `multiple_choice` (Heuristic mining).
- **Result:** Successfully extracted 100+ cases into `retrieval_dataset.yaml`.

### 3. Implementation: Phase 2 (Validator)
- **Task:** Create `validate_data.py`.
- **Method:** Implemented Monte Carlo Relevance Verification with Agentic Solving.
- **Features:**
    - **Decoupled Retrievers:** Uses a list of `AbstractRetriever` objects (GoldMiner, Embedding, Random) to build the candidate pool.
    - **Empirical Validation:** Runs Bernoulli trials (p=0.5). Injects context directly into prompt using `[START_DOCUMENT]` delimiters.
    - **Robust Generation:** Uses `JsonSanitizer` with schema injection and `response_schema` API enforcement.
    - **Causal Analysis:** Calculates `Delta P` (Impact Score) to identify relevant documents.
    - **Verified Results:** Successfully identified high-impact contexts (Delta P = +1.0) for MC questions.
- **Result:** Pipeline is fully operational and produces high-quality, verified retrieval benchmarks.

### 4. Implementation: Phase 3 (Evaluation)
- **Task:** Create `lib.py` shared models.
- **Method:** Defined `RetrievalResultMetadata` and `AbstractRetriever`.
- **Result:** Validated that Embeddings significantly outperform BM25 (Recall@5: 78% vs 21% on unverified data). Now ready for verified baseline.

### 5. Refactoring & Cleanup
- **Task:** Organized tools into `tools/retrieval_dataset_generation/`.
- **Refactoring:**
    - Moved `extract_retrieval_data.py` -> `extract_data.py`.
    - Moved `validate_retrieval_data.py` -> `validate_data.py`.
    - Moved `retrieval_benchmark_lib.py` -> `lib.py`.
    - Updated imports and `sys.path`.
- **Enhancement:** Added `confidence` stats (`n_in`, `se_in`, etc.) to metadata.
- **Adaptive Convergence:** Implemented an optional `adaptive` sampling mode that stops trials early once the standard error of impact scores stabilizes.
- **Verification:** Ran successful adaptive test on 1 case, converging at Trial 6.
- **Status:** Ready for full-scale generation.

### 6. Finalization (Robustness & Debugging)
- **Task:** Finalized `validate_data.py`.
- **Features:**
    - **Schema Injection:** Injects Pydantic schema JSON into prompts to guarantee structural compliance.
    - **API Enforcement:** Uses `response_schema` in `generate_content` config.
    - **Retry Logic:** Implemented exponential backoff for `429` errors.
    - **Validation:** Verified end-to-end on both API Understanding and Fix Error cases.
    - **Logging:** Added detailed logs for validation failures (Runner logs, Exceptions).
- **Result:** System is stable and ready for production use.

### 7. Rigorous Verification & Testing
- **Task:** Verify statistical assumptions and fix edge cases.
- **Improvements:**
    - **Adjusted Standard Error:** Implemented $1/N$ uncertainty for $p=0/1$ cases to prevent premature stopping on small N.
    - **Minimum Trials:** Increased `min_n` to 5 (Config default).
    - **Convergence Logic:** Restored `_check_convergence` method for testability.
    - **Bias Fix:** Removed logic that forced candidates into empty subsets, ensuring unbiased independent sampling.
    - **Tests:** Created unit tests for safety logic and integration tests for adaptive convergence.
- **Result:** System passes rigorous safety checks. Convergence requires substantial evidence.