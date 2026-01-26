# Retrieval Dataset Generation Tools

This package provides a comprehensive pipeline for mining, validating, and analyzing retrieval datasets from the ADK benchmark suite.

## Components

### 1. Extractor (`extract_data.py`)
Mines "Gold" candidates from benchmark ground truth and generates an initial dataset.
- **Input:** `ranked_targets.yaml`, `benchmarks/benchmark_definitions/**/*.yaml`
- **Output:** `retrieval_dataset.yaml` (Unverified)
- **Logic:**
    - For `api_understanding`: Extracts `fully_qualified_class_name`.
    - For `fix_errors`: Parses imports from `fixed.py`.
    - For `multiple_choice`: Heuristic mining from explanation/options.

### 2. Validator (`validate_data.py`)
Empirically verifies the relevance of candidate documents using Monte Carlo sampling and Causal Inference.
- **Input:** `retrieval_dataset.yaml`
- **Output:** `retrieval_dataset_verified.yaml`
- **Methodology:**
    - **Candidate Pooling:** Combines Gold candidates, Vector Search (Hard Negatives), and Random noise.
    - **Monte Carlo:** Runs `N=3` Bernoulli trials (p=0.5) per case, injecting randomized context subsets.
    - **Execution:** Uses `gemini-2.5-flash` to solve the task using *only* the injected context.
    - **Verification:** Uses `BenchmarkRunner` (Pytest/Regex) to objectively validate success.
    - **Impact Scoring:** Calculates `Delta P` (Success|In - Success|Out) to determine empirical relevance.

### 3. Library (`lib.py`)
Shared data models and retriever implementations.
- `RetrievalCase`: The core data structure.
- `RetrievalResultMetadata`: Statistical metrics (`delta_p`, `p_in`, `se_in`).
- `AbstractRetriever`: Interface for `GoldMiner`, `EmbeddingRetriever` (Vector Search), `RandomRetriever`.

## Metrics Guide

The validation process outputs statistical metrics in the metadata for each candidate document:

*   **`delta_p` (Impact Score):** The causal lift in success rate provided by this document.
    *   `> 0.05`: **Relevant (YES)**. The document helps.
    *   `~ 0.0`: **Irrelevant**. The document is noise.
    *   `< -0.05`: **Toxic**. The document actively confuses the model (e.g., outdated API).
*   **`p_in` / `p_out`:** Success probability when the document is present vs absent.
*   **`se_in` / `se_out`:** Standard Error of the probability estimates (confidence).

## Usage

```bash
# 1. Extract raw dataset from benchmarks
env/bin/python tools/retrieval_dataset_generation/extract_data.py

# 2. Validate and Score (This takes time and quota)
env/bin/python tools/retrieval_dataset_generation/validate_data.py
```
