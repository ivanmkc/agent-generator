# Design Doc: Retrieval Dataset Generation (Benchmark Mining)

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
Evaluating and optimizing the retrieval component of an RAG system requires a ground-truth dataset where the relevance of a document to a query is **empirically proven**, not just assumed from metadata. Furthermore, complex tasks often require **multiple** distinct pieces of information (a "Knowledge Kernel") rather than a single document.

**Goal:** Automate the extraction of a high-quality retrieval dataset by mining benchmarks and using a "Teacher Model" to rigorously label context relevance, supporting both single-hop and multi-hop scenarios.

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

## 6. Multi-Context Evolution (Progressive Kernel Expansion)

Many tasks require combining information from multiple sources (e.g., "Create an agent with a tool" needs `LlmAgent` *and* `FunctionTool`). A single positive document is insufficient. We need to establish the **Required Kernel** (the minimal set of documents needed to answer the question).

### 6.1 Method: Progressive Expansion
We evolve the dataset from single-doc mappings to multi-doc sets.

**Algorithm:**
1.  **Initial Seed:** Start with the primary target (e.g., `LlmAgent`).
2.  **Sufficiency Check:** Ask Judge: "Can you answer Q with just {LlmAgent}?"
    *   *Judge:* "No, I need to know how to define a tool."
3.  **Expansion:** Search for the missing concept (e.g., "tool definition"). Add candidates (e.g., `FunctionTool`) to the candidate set.
4.  **Set Validation:** Ask Judge: "Can you answer Q with {LlmAgent, FunctionTool}?"
    *   *Judge:* "Yes." -> **Kernel Established: {LlmAgent, FunctionTool}**.

### 6.2 Alternative Proposals for Expansion

#### Proposal A: Static Import Mining (Fastest)
*   **Logic:** For `fix_error` cases, the solution code (`fixed.py`) contains imports.
*   **Assumption:** Every imported ADK class is part of the required kernel.
*   **Pros:** Fast, no LLM required for discovery.
*   **Cons:** Over-inclusion (some imports might be utility/optional).

#### Proposal B: Agent-Driven Discovery (Most Robust)
*   **Logic:** An `Agent` attempts to solve the task. Every time it searches/inspects a class and *uses* it in the final solution, add that class to the Kernel.
*   **Pros:** Captures the actual retrieval path.
*   **Cons:** Expensive and slow.

### 6.3 Multi-Context Metrics

When the ground truth is a **Set** (`G = {d1, d2, ...}`), standard Recall@K is insufficient.

#### Metric 1: Set Recall (Kernel Completeness)
*   **Definition:** The fraction of the *Required Kernel* found in the top K results.
*   **Formula:** `|Retrieved_TopK ∩ Gold_Set| / |Gold_Set|`
*   **Example:** Gold={A, B}. Retrieved={A, C, D}. Overlap={A}. Set Recall = 1/2 = 50%.
*   **Target:** We want Set Recall = 100% (The agent has *all* necessary pieces).

#### Metric 2: Success@K (Binary)
*   **Definition:** 1 if `Set Recall == 100%`, else 0.
*   **Why:** If even one piece is missing, the agent might fail. This is a stricter metric.

#### Metric 3: Jaccard Similarity
*   **Definition:** Intersection over Union between Retrieved and Gold sets.
*   **Formula:** `|Retrieved ∩ Gold| / |Retrieved ∪ Gold|`
*   **Why:** Penalizes fetching too much noise (Precision) while rewarding completeness (Recall).