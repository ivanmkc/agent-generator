# Design Doc: Retrieval Dataset Generation (Benchmark Mining)

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
Evaluating and optimizing the retrieval component of an RAG system requires a ground-truth dataset where the relevance of a document to a query is **empirically proven**, not just assumed from metadata.

**Goal:** Automate the extraction of a high-quality retrieval dataset by mining benchmarks and using a "Teacher Model" (Gemini 3 Pro) to rigorously label context relevance.

## 2. Methodology: Empirical Relevance Validation

We do not trust that a class mentions in a benchmark answer is the *only* relevant context, nor that random documents are truly irrelevant. We determine relevance dynamically.

### 2.1 The Pipeline

```text
+-------------------------+       +-------------------------+
|   Benchmark Registry    | ----> |   Question Extractor    |
| (YAML/JSON Definitions) |       | (Iterates all cases)    |
+-------------------------+       +------------+------------+
                                            |
                                            v
                                   +-----------------+
                                   |  Context Pool   |
                                   | (Gold + Random) |
                                   +-----------------+
                                            |
                                            v
+-----------------------+       +-------------------------+
|   Relevance Judge     | <---- | Pair: (Question, Ctx)   |
| (Gemini 3 Pro)        |       |                         |
+-----------------------+       +-------------------------+
            |
            v
    [ Labeled Tuple: (Q, Ctx, Label: RELEVANT/IRRELEVANT) ]
```

### 2.2 Validation Logic (The Judge)

For each Question `Q` extracted from a benchmark:
1.  **Candidate Selection:**
    *   Select the "Target Class" (from benchmark metadata).
    *   Select `N` "Random Classes" (potential negatives).
    *   Select `M` "Hard Negatives" (BM25 top hits that aren't the target).

2.  **LLM Judgment (Empirical Labeling):**
    *   **Model:** `gemini-3-pro-preview`.
    *   **Prompt:**
        > "User Question: {Q}
        > Context: {Ctx}
        > Task: Can you answer the user's question definitively using ONLY the provided context?
        > Answer 'YES' only if the context contains the specific answer/code. Answer 'NO' if it is missing or irrelevant."
    *   **Outcome:**
        *   **YES:** Context is **Positive**.
        *   **NO:** Context is **Negative**.

### 2.3 Embedding Configuration
When benchmarking or training using this dataset, strictly adhere to task-specific embedding types to maximize performance.

*   **Model:** `models/text-embedding-004` (or user-specified strongest).
*   **Task Types:**
    *   **Queries:** `RETRIEVAL_QUERY` (or `CODE_RETRIEVAL_QUERY` for code-heavy tasks).
    *   **Documents:** `RETRIEVAL_DOCUMENT`.

## 3. Dataset Schema

The output `retrieval_dataset.yaml`:

```yaml
pairs:
  - id: "fix_errors:01"
    query: "How do I create a minimal LlmAgent?"
    # Verified by Gemini 3 Pro to contain the answer
    positive_ctxs:
      - fqn: "google.adk.agents.llm_agent.LlmAgent"
        text: "..."
    # Verified by Gemini 3 Pro to NOT contain the answer
    negative_ctxs:
      - fqn: "google.adk.plugins.RetryPlugin"
        text: "..."
```

## 4. Implementation Plan

### Phase 1: The Extractor (`tools/extract_retrieval_data.py`)
- **Action:** Update to fetch candidates but NOT label them yet.

### Phase 2: The Judge (`tools/validate_retrieval_data.py`)
- **Input:** Raw Candidates (Q, [Ctx1, Ctx2...]).
- **Action:** Parallel calls to `gemini-3-pro-preview` to label each context.
- **Output:** Verified `retrieval_dataset.yaml`.

### Phase 3: Evaluation (`notebooks/evaluate_retrieval.ipynb`)
- **Action:** Update `EmbeddingRetriever` to use `task_type="RETRIEVAL_QUERY"` for queries and `task_type="RETRIEVAL_DOCUMENT"` for indexing.

## 5. Metrics
*   **Recall@K:** Fraction of queries where at least one *Empirically Positive* document is in Top-K.
*   **Precision@K:** Fraction of retrieved documents in Top-K that are *Empirically Positive*.
