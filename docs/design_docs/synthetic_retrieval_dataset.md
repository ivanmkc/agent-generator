# Design Doc: Retrieval Dataset Generation (Benchmark Mining)

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
Evaluating and optimizing the retrieval component of an RAG system (like `search_ranked_targets`) requires a high-quality dataset of `(Query, Relevant_Document)` pairs. While synthetic generation is possible, we already possess a rich corpus of human-verified questions in our benchmark suite.

**Goal:** Automate the extraction of a high-quality, task-aligned retrieval dataset by mining existing benchmark definitions (`api_understanding`, `fix_error`, etc.).

## 2. Methodology: Benchmark Mining

Instead of hallucinating new questions, we treat the existing benchmark questions as the "Query" and their associated correct answers/targets as the "Gold Context".

### 2.1 The Pipeline

```text
+-------------------------+       +-------------------------+
|   Benchmark Registry    | ----> |   Question Extractor    |
| (YAML/JSON Definitions) |       | (Iterates all cases)    |
+-------------------------+       +------------+------------+
                                            |
                                            v
                                   +-----------------+
                                   |  Target Mapper  |
                                   | (Links Q -> FQN)|
                                   +-----------------+
                                            |
                                            v
+-----------------------+       +-------------------------+
|   Validation Filter   | <---- | Pair: (Question, FQN)   |
| (Forward RAG Check)   |       |                         |
+-----------------------+       +-------------------------+
            |
            v
    [ Verified Tuple: (Q, Gold_Docstring, Hard_Negatives) ]
```

### 2.2 Extraction Logic

#### A. Multiple Choice (`api_understanding`)
These are the highest quality sources because they explicitly link a question to a class FQN.
*   **Source:** `benchmarks/benchmark_definitions/api_understanding/benchmark.yaml`
*   **Query:** The `question` field (e.g., "Which class is used to run multiple agents concurrently?").
*   **Gold Context:** The `fully_qualified_class_name` list in the `answers` section (e.g., `google.adk.agents.ParallelAgent`).

#### B. Fix Error Cases (`fix_errors`)
These represent complex "How-To" coding tasks.
*   **Source:** `benchmarks/benchmark_definitions/fix_errors/benchmark.yaml`
*   **Query:** The `description` or `name` (e.g., "Create a LoopAgent that runs a sub-agent a fixed number of times.").
*   **Gold Context:** Inferred from the imports in `fixed.py` or `test_agent.py`. We can use a lightweight LLM call to extract the "Primary Subject Class" from the solution code (e.g., `google.adk.agents.LoopAgent`).

### 2.3 Step-by-Step Workflow

1.  **Harvesting:**
    *   Iterate through all benchmark YAMLs.
    *   Extract `(question_text, target_fqn_hints)`.

2.  **Resolution:**
    *   Resolve `target_fqn_hints` to an actual entry in `ranked_targets.yaml`.
    *   Retrieve the full docstring/signature for that target.

3.  **Negative Sampling:**
    *   Select 5 random *other* targets from `ranked_targets.yaml`.
    *   **Hard Negatives:** Select targets sharing the same parent module but different class (e.g., `SequentialAgent` when the target is `ParallelAgent`).

4.  **Validation:**
    *   Verify that the "Gold Context" actually contains the answer to the question (crucial for ensuring the link is valid).

## 3. Dataset Schema

The output will be a JSONL file (`retrieval_dataset.jsonl`):

```json
{
  "id": "api_understanding:which_class_is_parallel",
  "source": "benchmark_mining",
  "query": "Which class is used to run multiple agents concurrently?",
  "positive_ctxs": [
    {
      "fqn": "google.adk.agents.ParallelAgent",
      "text": "The ParallelAgent runs..."
    }
  ],
  "negative_ctxs": [
    {
      "fqn": "google.adk.agents.SequentialAgent",
      "text": "The SequentialAgent runs..."
    }
  ]
}
```

## 4. Implementation Plan

### Phase 1: The Extractor Script (`tools/extract_retrieval_data.py`)
- Load all benchmarks.
- Implement specific extractors for `api_understanding` (direct map) and `fix_error` (inference).
- Load `ranked_targets.yaml` to fetch docstrings.

### Phase 2: Evaluation
- Use this dataset to benchmark:
    - Current `search_ranked_targets` (BM25).
    - Proposed `VectorSearchProvider` (Embeddings).
- Metric: **Recall@K** (Is the correct class in the top K results?).

## 5. Benefits
- **Realism:** Evaluates retrieval on the *exact* types of questions agents are being asked to solve.
- **Efficiency:** No need to generate synthetic questions from scratch; leverage the manual effort already put into benchmarks.
- **Coverage:** Ensures the retrieval system covers all "examinable" parts of the API.