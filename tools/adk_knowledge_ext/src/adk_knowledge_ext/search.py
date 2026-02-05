"""Search module."""

import logging
import re
import os
import json
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class SearchProvider(ABC):

    @abstractmethod
    def build_index(self, items: List[Dict[str, Any]]):
        """Builds the search index from the list of items."""
        pass

    @abstractmethod
    async def search(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """Searches for the query and returns paginated (score, item) tuples."""
        pass

    async def has_matches(self, query: str) -> bool:
        """Checks if the query yields any matches (ignoring pagination)."""
        # Default implementation: search first page with size 1
        res = await self.search(query, page=1, page_size=1)
        return len(res) > 0


class BM25SearchProvider(SearchProvider):

    def __init__(self):
        self._bm25_index = None
        self._corpus_map = []  # Maps corpus index to original item index
        self._items = []

    def build_index(self, items: List[Dict[str, Any]]):
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning(
                "rank_bm25 not installed. BM25SearchProvider cannot function."
            )
            return

        self._items = items
        tokenized_corpus = []
        self._corpus_map = []

        for i, item in enumerate(items):
            fqn = item.get("id") or item.get("fqn") or item.get("name")
            if fqn:
                # Tokenize FQN by dot and underscore to expose class names
                fqn_parts = " ".join(re.split(r"[._]", fqn))
                doc_text = f"{fqn_parts} {fqn} {fqn} {fqn} " + (
                    item.get("docstring") or ""
                )
                tokenized_corpus.append(doc_text.lower().split())
                self._corpus_map.append(i)

        if tokenized_corpus:
            self._bm25_index = BM25Okapi(tokenized_corpus)
            logger.info(f"BM25 Index built with {len(tokenized_corpus)} items.")

    async def has_matches(self, query: str) -> bool:
        if not self._bm25_index:
            return False
        tokenized_query = query.lower().split()
        scores = self._bm25_index.get_scores(tokenized_query)
        return any(s > 0 for s in scores)

    async def search(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
        if not self._bm25_index:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25_index.get_scores(tokenized_query)

        scored_items = []
        for idx, score in enumerate(scores):
            if score > 0:
                real_idx = self._corpus_map[idx]
                item = self._items[real_idx]
                scored_items.append((score, item))

        scored_items.sort(
            key=lambda x: (-x[0], x[1].get("rank", 9999), x[1].get("id", ""))
        )

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        return scored_items[start_idx:end_idx]


class KeywordSearchProvider(SearchProvider):
    """
    A simple keyword-based search provider that scores items based on term frequency and location.

    Algorithm:
    1. Tokenizes the query into lowercase keywords.
    2. Iterates through all indexed items.
    3. Calculates a score for each item:
       - +10 points if a keyword appears in the FQN (Fully Qualified Name).
       - +20 points (additional) if the FQN ends with the keyword (exact class/method match).
       - +5 points if a keyword appears in the docstring summary.
    4. Sorts results by score (descending), then rank (ascending), then ID (ascending) for determinism.
    5. Returns a paginated slice of the results.
    """

    def __init__(self):
        self._items = []

    def build_index(self, items: List[Dict[str, Any]]):
        """
        Stores the list of items in memory for linear scanning.
        
        Args:
            items: A list of dictionaries representing the targets. Each item must have 'id' (or 'fqn'/'name')
                   and optionally 'docstring' and 'rank'.
        """
        self._items = items
        logger.info("Keyword Search Index ready.")

    async def search(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        Performs a linear scan search over the indexed items.

        Args:
            query: The search string containing one or more keywords.
            page: The 1-based page number to return.
            page_size: The number of results per page.

        Returns:
            A list of tuples (score, item) for the matching results on the requested page.
        """
        matches = []
        keywords = query.lower().split()

        for item in self._items:
            fqn_raw = item.get("id") or item.get("fqn") or item.get("name") or ""
            fqn = fqn_raw.lower()
            summary = item.get("docstring", "").lower()

            score = 0
            for kw in keywords:
                if kw in fqn:
                    score += 10
                    if fqn.endswith(kw) or fqn.endswith("." + kw):
                        score += 20
                elif kw in summary:
                    score += 5

            if score > 0:
                matches.append((score, item))

        matches.sort(key=lambda x: (-x[0], x[1].get("rank", 9999), x[1].get("id", "")))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        return matches[start_idx:end_idx]


class VectorSearchProvider(SearchProvider):
    """
    A semantic search provider using vector embeddings (cosine similarity).

    Algorithm:
    1. Loads pre-computed embeddings (numpy array) and metadata (JSON) from disk.
    2. Embeds the search query using the Google GenAI API (text-embedding-004 or fallback).
    3. Computes the dot product (cosine similarity) between the query vector and all item vectors.
    4. Filters results below a minimal threshold (0.1) to reduce noise.
    5. Sorts by similarity score (descending) and returns a paginated slice.
    """
    def __init__(self, index_dir: Path, api_key: Optional[str] = None):
        self.vectors = None
        self.metadata = None
        self.index_dir = index_dir
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = None
        self._items_map = {}

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not found.")
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def build_index(self, items: List[Dict[str, Any]]):
        """
        Loads the vector index artifacts from the specified directory.
        
        Args:
            items: The full list of items (used here only to build a lookup map for retrieving full item details).
        """
        # Load from disk if exists, otherwise we can't build it here (requires embeddings)
        # We assume build_vector_index.py was run.
        vectors_path = self.index_dir / "targets_vectors.npy"
        meta_path = self.index_dir / "targets_meta.json"

        if vectors_path.exists() and meta_path.exists():
            self.vectors = np.load(vectors_path)
            with open(meta_path, "r") as f:
                self.metadata = json.load(f)
            
            # Map items for quick lookup
            self._items_map = {item.get("id") or item.get("fqn"): item for item in items}
            logger.info(f"Vector Index loaded with {len(self.vectors)} items.")
        else:
            logger.warning(f"Vector index files not found in {self.index_dir}")

    async def search(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
        if self.vectors is None or not self.metadata:
            return []

        client = self._get_client()
        from google.genai import types

        # 1. Embed query
        try:
            # Try text-embedding-004, then fallback
            try:
                response = client.models.embed_content(
                    model="text-embedding-004",
                    contents=query,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
                )
            except Exception:
                response = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=query,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
                )
            
            query_vec = np.array(response.embeddings[0].values)
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            return []

        # 2. Compute Cosine Similarity (Dot product on normalized vectors)
        # Assuming vectors are already normalized (standard for embeddings)
        # If not, we should normalize them. 
        # For now, let's just do dot product and sort.
        scores = np.dot(self.vectors, query_vec)
        
        # 3. Top-K across ALL items first, then paginate
        # We need ALL results above some threshold or just top-K
        # Vector search doesn't really have "no matches" unless we threshold
        scored_items = []
        for i, score in enumerate(scores):
            # Use a small threshold to prune irrelevant results
            if score > 0.1:
                meta = self.metadata[i]
                fqn = meta["id"]
                item = self._items_map.get(fqn)
                if item:
                    scored_items.append((float(score), item))

        scored_items.sort(key=lambda x: -x[0])

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        return scored_items[start_idx:end_idx]


class CompositeSearchProvider(SearchProvider):
    """
    A composite provider that delegates to a list of providers in order of priority.

    Strategy:
    Iterates through the provided list of search providers. The first provider
    that returns matches (via `has_matches` or non-empty `search`) is used to
    fulfill the request. This implements a "waterfall" or "fallback" logic.
    """

    def __init__(self, providers: List[SearchProvider]):
        self._providers = providers

    def build_index(self, items: List[Dict[str, Any]]):
        for provider in self._providers:
            provider.build_index(items)

    async def search(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
        for provider in self._providers:
            provider_name = provider.__class__.__name__
            if await provider.has_matches(query):
                logger.info(f"Search provider '{provider_name}' matched for query: '{query}'")
                return await provider.search(query, page, page_size)
            else:
                logger.info(f"Search provider '{provider_name}' had no matches for query: '{query}'. Falling back...")

        logger.warning(f"No search providers matched for query: '{query}'")
        # If no provider matches, return empty from the last one (or empty list)
        return []