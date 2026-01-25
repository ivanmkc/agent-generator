# Design Doc: Retrieval Dataset Generation (Benchmark Mining)

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
Evaluating and optimizing the retrieval component of an RAG system requires a ground-truth dataset where the relevance of a document to a query is **empirically proven** via statistical causal inference, rather than assumed from metadata or subjective LLM judgment.

**Goal:** Automate the extraction of a high-quality retrieval dataset by mining benchmarks and using a **Monte Carlo Verification** process to establish the conditional dependence of task success on specific documents.

## 2. Methodology: Monte Carlo Relevance Verification

We treat all potential documents (whether seeded from benchmark metadata or randomly sampled) as **candidates**. Their status as "Relevant" or "Irrelevant" is determined solely by whether their presence causally increases the probability of solving the task.

### 2.1 The Pipeline

```text
+-------------------------+       +-------------------------+
|   Benchmark Registry    | ----> |   Candidate Pooler      |
| (YAML/JSON Definitions) |       | (Mixes Seeded + Random) |
+-------------------------+       +------------+------------+
                                            |
                                            v
                                   +-----------------+
                                   |  Monte Carlo    |
                                   |  Sampler (Loop) |
                                   +-----------------+
                                            |
                                            v
                                   +-----------------+
                                   |  Blind Solver   |
                                   |  (Attempts Task)|
                                   +-----------------+
                                            |
                                            v
    [ Result Log: (Context_Subset, Success/Fail) ] --> [ Statistical Analyzer ]
                                                              |
                                                              v
                                                [ Verified Tuple: (Q, Relevant_Set) ]
```

### 2.2 The Algorithm

For each Question `Q`:

1.  **Candidate Pooling:**
    *   Let `C_seed` be the targets identified in the benchmark metadata (e.g., imports).
    *   Let `C_random` be a set of randomly sampled targets.
    *   `Pool = C_seed ∪ C_random`. All items are treated identically.

2.  **Monte Carlo Trials:**
    *   Run `N` trials (e.g., N=10).
    *   In each trial `i`:
        *   Randomly select a subset `S_i` from `Pool` (e.g., Bernoulli trial with p=0.5 for each item).
        *   Prompt the **Blind Solver** (Gemini 3 Pro) to answer `Q` using *only* context `S_i`.
        *   Validate the answer against the Ground Truth (using `ApiUnderstandingRunner` or `PytestRunner`).
        *   Record `Result_i = 1` (Pass) or `0` (Fail).

3.  **Statistical Analysis (Conditional Dependence):**
    *   For each document `d` in `Pool`:
        *   `Success_In`: Mean success rate of trials where `d ∈ S_i`.
        *   `Success_Out`: Mean success rate of trials where `d ∉ S_i`.
        *   `Delta_P = Success_In - Success_Out`.
    *   **Verdict:**
        *   If `Delta_P > Threshold` (e.g., 0.1), `d` is **Relevant**.
        *   Otherwise, `d` is **Irrelevant** (Distractor).

### 2.3 Benefit
This approach eliminates "Hallucinated Relevance" (where an LLM *says* a doc is useful but doesn't actually need it) and "Missing Necessity" (where a doc is useful but not strictly required if the model has internal knowledge). It only keeps documents that **actually help**.

## 3. Dataset Schema

The output `retrieval_dataset.yaml`:

```yaml
pairs:
  - id: "fix_errors:01"
    query: "How do I create a minimal LlmAgent?"
    candidates:
      - fqn: "google.adk.agents.llm_agent.LlmAgent"
        text: "..."
        empirical_relevance: "YES"
        delta_p: 0.85  # Presence increased success by 85%
      - fqn: "google.adk.plugins.RetryPlugin"
        text: "..."
        empirical_relevance: "NO"
        delta_p: 0.02  # Statistical noise
    metadata:
      trials: 10
      base_success_rate: 0.1
```

## 4. Implementation Plan

### Phase 1: The Extractor (`tools/extract_retrieval_data.py`)
- Extracts `GroundTruth` data (test files, answer templates) required for the validator to run actual checks.
- Generates the initial candidate pool.

### Phase 2: The Validator (`tools/validate_retrieval_data.py`)
- Implements the Monte Carlo loop.
- Uses `benchmarks.benchmark_runner` to perform the actual validation logic (reusing existing infra).
- Calculates `Delta_P` and annotates the dataset.

### Phase 3: Evaluation
- Standard Recall/Precision metrics are calculated against the set of documents marked `empirical_relevance: "YES"`.

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
