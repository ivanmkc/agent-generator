# Design Doc: Vector Search Backend for Ranked Targets

**Status:** Draft
**Author:** Gemini CLI Agent
**Date:** 2026-01-24

## 1. Problem Statement
The current `search_ranked_targets` tool relies on keyword matching (BM25/Fuzzy). While effective for exact symbol lookups (e.g., "LlmAgent"), it fails on semantic queries (e.g., "how to save session state", "retry tool execution") where the user's intent doesn't match the exact class names.

**Goal:** Implement a semantic search backend using vector embeddings to enable natural language discovery of ADK components.

## 2. Solution Architecture

The solution involves an offline indexing pipeline and a runtime semantic search provider.

### 2.1 Component Diagram

```text
+----------------------+       +-------------------------+
|  ranked_targets.yaml | ----> |   Embedding Generator   |
| (Source Knowledge)   |       | (tools/build_index.py)  |
+----------------------+       +------------+------------+
                                            |
                                            v
                                   +-----------------+
                                   |  Gemini API     |
                                   | (Embeddings)    |
                                   +-----------------+
                                            |
                                            v
+----------------------+       +-------------------------+
|   AdkTools Runtime   | <---- |  Vector Store           |
| (search_ranked_targets)|     | (embeddings.npy + meta) |
+----------------------+       +-------------------------+
```

## 3. Implementation Strategy

### 3.1 The Embedding Model
We will use **Google Gemini Embeddings** (`models/text-embedding-004` or latest) for high-quality semantic capture.

### 3.2 The Vector Store (Lightweight)
Since `ranked_targets.yaml` contains < 2,000 entries, a heavy vector DB (Pinecone, Milvus) is overkill.
*   **Storage:** A simple local file structure in `.gemini/cache/`:
    *   `targets_vectors.npy`: A NumPy array of shape `(N, D)`.
    *   `targets_meta.json`: A list of dictionaries mapping index `i` to `{"fqn": "...", "type": "..."}`.
*   **Search Algorithm:** Exact cosine similarity (dot product of normalized vectors) using NumPy or Scikit-Learn.

### 3.3 The Indexing Script (`tools/build_vector_index.py`)
1.  Load `ranked_targets.yaml`.
2.  For each target, construct a "rich text representation":
    ```text
    Name: {name}
    Type: {type}
    Docstring: {docstring_summary}
    Signatures: {method_signatures}
    ```
3.  Batch calls to `client.models.embed_content`.
4.  Save artifacts to the cache directory.

### 3.4 The Runtime Provider (`VectorSearchProvider`)
A new class implementing the `SearchProvider` protocol.

```python
class VectorSearchProvider(SearchProvider):
    def __init__(self, index_path: Path, api_key: str):
        self.vectors = np.load(index_path / "vectors.npy")
        self.metadata = json.load(index_path / "meta.json")
        self.client = genai.Client(api_key=api_key)

    async def search(self, query: str, limit: int = 5) -> List[RankedTarget]:
        # 1. Embed query
        query_vec = await self.client.models.embed_content(
            model="text-embedding-004", content=query
        )
        
        # 2. Compute Cosine Similarity
        scores = np.dot(self.vectors, query_vec)
        
        # 3. Top-K
        top_indices = np.argsort(scores)[-limit:][::-1]
        
        # 4. Map to Targets
        return [self._map_to_target(i, scores[i]) for i in top_indices]
```

## 4. Integration Plan

### Phase 1: Index Generation
*   Create `tools/build_vector_index.py`.
*   Run it in CI/CD or manually to generate the initial index.
*   Check in the index artifacts (or cache them).

### Phase 2: Runtime Integration
*   Modify `AdkTools` to initialize `VectorSearchProvider` if the index exists and an API key is present.
*   Update `search_ranked_targets` to use a **Hybrid Strategy**:
    *   If query looks like code (e.g., "LlmAgent"), favor BM25.
    *   If query looks like natural language, favor Vector Search.
    *   Or simpler: Merge results from both (Reciprocal Rank Fusion).

### Phase 3: Benchmark
*   Create `benchmark_definitions/search_relevance` to test queries like "how to retry".
*   Verify that `ReflectAndRetryToolPlugin` appears in the top results.

## 5. Security & Costs
*   **API Cost:** Indexing 2,000 targets is negligible (~$0.02). Runtime queries are also cheap.
*   **Leakage:** Ensure no internal/private targets are indexed if they shouldn't be exposed.

## 6. Future Work
*   **Hybrid Search (RRF):** Combine BM25 and Vector scores for robust retrieval.
*   **Contextual Reranking:** Use a lightweight Cross-Encoder to rerank the top 20 vector results.
