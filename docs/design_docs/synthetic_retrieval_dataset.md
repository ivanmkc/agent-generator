# Design Doc: Synthetic Retrieval Dataset Generation (Reverse RAG)

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
Evaluating and optimizing the retrieval component of an RAG system (like `search_ranked_targets`) requires a high-quality dataset of `(Query, Relevant_Document)` pairs. Manually creating this for the ADK codebase is labor-intensive.

**Goal:** Automate the generation of a high-quality, domain-specific retrieval dataset by synthetically "reversing" the RAG process.

## 2. Methodology: Reverse RAG Generation

The core idea is to start with the *answer* (a code snippet or docstring) and generate the *question* that would lead to it.

### 2.1 The Pipeline

```text
+-----------------------+       +-------------------------+
|   ADK Codebase / Docs | ----> |   Context Sampler       |
|   (ranked_targets)    |       | (Selects 'Gold Chunk')  |
+-----------------------+       +------------+------------+
                                            |
                                            v
                                   +-----------------+
                                   |  Question Gen   |
                                   |  (LLM Agent)    |
                                   +-----------------+
                                            |
                                            v
+-----------------------+       +-------------------------+
|   Validation Filter   | <---- | Generated Question      |
| (Forward RAG Check)   |       | + Gold Chunk            |
+-----------------------+       +-------------------------+
            |
            v
    [ Verified Tuple: (Q, Gold_Ctx, Hard_Negatives) ]
```

### 2.2 Step-by-Step Workflow

1.  **Sampling (The Anchor):**
    *   Select a target from `ranked_targets.yaml` (e.g., `google.adk.plugins.RetryPlugin`).
    *   Extract its docstring and signature as the "Gold Context".

2.  **Synthetic Question Generation:**
    *   **Prompt:** "You are a developer using the Google ADK. Write a natural language question or search query where the answer is explicitly found in the following context. Do not mention the class name directly in the query if possible (simulate a discovery intent)."
    *   *Input:* `RetryPlugin` docstring.
    *   *Output:* "How do I automatically retry a tool if it fails?"

3.  **Negative Sampling:**
    *   Select 5 random *other* targets (e.g., `LlmAgent`, `VectorSearch`).
    *   **Hard Negatives:** Select targets with similar names but different functions (e.g., `ReflectRetryToolPlugin` vs `RetryPlugin` if they differ).

4.  **Validation (The Filter):**
    *   **Test A (Solvability):** Can an LLM answer the question given *only* the Gold Context? (Must be Yes).
    *   **Test B (Necessity):** Can an LLM answer the question given *only* the Negative Contexts? (Must be No/Hallucinated).
    *   *Action:* If Test A passes and Test B fails, add to dataset.

## 3. Dataset Schema

The output will be a JSONL file (`retrieval_dataset.jsonl`):

```json
{
  "id": "q_12345",
  "query": "How do I automatically retry a tool if it fails?",
  "positive_ctxs": [
    {
      "fqn": "google.adk.plugins.RetryPlugin",
      "text": "The RetryPlugin automatically retries..."
    }
  ],
  "negative_ctxs": [
    {
      "fqn": "google.adk.agents.LlmAgent",
      "text": "The LlmAgent is the core..."
    }
  ],
  "generated_answer": "You can use the RetryPlugin..."
}
```

## 4. Implementation Plan

### Phase 1: The Generator Script (`tools/generate_retrieval_data.py`)
- Load `ranked_targets.yaml`.
- Iterate through top N targets (or random sample).
- Use `gemini-2.5-flash` for fast generation and validation.

### Phase 2: Evaluation
- Use this dataset to benchmark:
    - Current `search_ranked_targets` (BM25).
    - Proposed `VectorSearchProvider` (Embeddings).
- Metric: **Recall@K** (Is the Gold Context in the top K results?).

### Phase 3: Training (Optional)
- Fine-tune a BGE-M3 or E5 embedding model using the triplets if off-the-shelf performance is insufficient.

## 5. Applications
- **Regression Testing:** Ensure new search algorithms don't break discovery of core components.
- **Search Suggestions:** Use the synthetic queries to populate "Did you mean?" vectors.
