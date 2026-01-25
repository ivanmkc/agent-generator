# Design Doc: Retrieval Dataset Generation (Benchmark Mining)

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
Evaluating and optimizing the retrieval component of an RAG system (like `search_ranked_targets`) requires a high-quality dataset of `(Query, Relevant_Document)` pairs. While synthetic generation is possible, we already possess a rich corpus of human-verified questions in our benchmark suite.

**Goal:** Automate the extraction of a high-quality, task-aligned retrieval dataset by mining existing benchmark definitions (`api_understanding`, `fix_error`, etc.) and establish a rigorous evaluation framework.

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

### 2.3 Validation & Filtering
Not all benchmark questions are good retrieval queries. We filter candidates using a "Forward RAG Check":
1.  **Sufficiency Check:** Can an LLM answer the question given *only* the mapped Gold Context?
    *   *If No:* The context mapping is wrong or the docstring is insufficient. Discard.
2.  **Necessity Check:** Can an LLM answer the question given *random* contexts?
    *   *If Yes:* The question is too generic or relies on common knowledge. Discard.

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
      "text": "The ParallelAgent runs...",
      "rank_relevance": 1  // Primary target
    }
  ],
  "negative_ctxs": [
    {
      "fqn": "google.adk.agents.SequentialAgent",
      "text": "The SequentialAgent runs...",
      "is_hard_negative": true
    }
  ],
  "metadata": {
    "difficulty": "medium",
    "required_concepts": ["agents", "concurrency"]
  }
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

## 5. Metrics & Evaluation Framework

To rigorously assess the retrieval quality, we will calculate the following metrics for each search algorithm.

### 5.1 Recall at K (Recall@K)
**Definition:** The proportion of queries where the *relevant* document appears in the top `K` results.
*   **Formula:** `1` if Gold Context in Top-K else `0`. (Averaged over all queries).
*   **Why it matters:** For an LLM Agent, if the correct tool/class isn't in the context window (Top-K), the agent *cannot* solve the task. This is the **primary metric**.
*   **Targets:**
    *   **Recall@1:** Perfect retrieval. (Ideal target: > 60%)
    *   **Recall@5:** "Good enough" for an LLM to filter. (Ideal target: > 90%)

### 5.2 Precision at K (Precision@K)
**Definition:** The proportion of retrieved documents in the top `K` that are relevant.
*   **Formula:** `(Number of Relevant Docs in Top-K) / K`.
*   **Why it matters:** Low precision means the context window is filled with "noise" (distractors). This wastes tokens, increases cost, and can confuse the LLM (hallucination risk).
*   **Trade-off:** We often sacrifice some Precision to maximize Recall, relying on the LLM to filter noise.

### 5.3 Mean Reciprocal Rank (MRR)
**Definition:** The average of the reciprocal ranks of the *first* relevant document.
*   **Formula:** `1 / Rank_of_First_Correct_Result`. (e.g., if correct result is at #1, score 1.0; at #2, score 0.5).
*   **Why it matters:** MRR rewards algorithms that put the right answer at the *very top*. This is crucial for Latency (agent stops searching earlier) and Trust.

### 5.4 Normalized Discounted Cumulative Gain (NDCG@K)
**Definition:** A measure of ranking quality that accounts for the *position* of all relevant documents, giving higher weight to those near the top.
*   **Why it matters:** Unlike Recall (binary), NDCG handles cases with *multiple* valid answers (e.g., `LlmAgent` and `BaseAgent` might both be relevant). It penalizes the system if the "best" answer is lower down the list.

### 5.5 Failure Analysis Categories
We will classify retrieval failures into buckets:
1.  **Vocabulary Mismatch:** User used synonyms not present in docstring (e.g., "concurrent" vs "parallel"). -> *Fix: Vector Search.*
2.  **Specificity Gap:** Query was too vague ("How to run agent") for a specific target (`ParallelAgent`). -> *Fix: Query Expansion.*
3.  **Distractor Overlap:** A hard negative (`SequentialAgent`) scored higher due to shared keywords. -> *Fix: Reranking / Contrastive Training.*
