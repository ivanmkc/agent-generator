"""Search module."""

import logging
import re
from typing import List, Dict, Any, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SearchProvider(ABC):

    @abstractmethod
    def build_index(self, items: List[Dict[str, Any]]):
        """Builds the search index from the list of items."""
        pass

    @abstractmethod
    def search(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """Searches for the query and returns paginated (score, item) tuples."""
        pass

    def has_matches(self, query: str) -> bool:
        """Checks if the query yields any matches (ignoring pagination)."""
        # Default implementation: search first page with size 1
        return len(self.search(query, page=1, page_size=1)) > 0


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
                # e.g. "google.adk.Tool" -> "google adk Tool"
                fqn_parts = " ".join(re.split(r"[._]", fqn))

                # Create a rich text representation for search
                # FQN gets boosted by repetition
                doc_text = f"{fqn_parts} {fqn} {fqn} {fqn} " + (
                    item.get("docstring") or ""
                )
                tokenized_corpus.append(doc_text.lower().split())
                self._corpus_map.append(i)

        if tokenized_corpus:
            self._bm25_index = BM25Okapi(tokenized_corpus)
            logger.info(f"BM25 Index built with {len(tokenized_corpus)} items.")

    def has_matches(self, query: str) -> bool:
        if not self._bm25_index:
            return False
        tokenized_query = query.lower().split()
        scores = self._bm25_index.get_scores(tokenized_query)
        # Optimized check: any score > 0
        return any(s > 0 for s in scores)

    def search(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
        if not self._bm25_index:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25_index.get_scores(tokenized_query)

        # Zip scores with index
        scored_items = []
        for idx, score in enumerate(scores):
            if score > 0:
                # real_idx maps back to original item in self._items
                real_idx = self._corpus_map[idx]
                item = self._items[real_idx]
                scored_items.append((score, item))

        # Deterministic Sort: Score DESC, then Rank ASC, then ID ASC
        scored_items.sort(
            key=lambda x: (-x[0], x[1].get("rank", 9999), x[1].get("id", ""))
        )

        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        matches = []
        for score, item in scored_items[start_idx:end_idx]:
            matches.append((score, item))

        return matches


class KeywordSearchProvider(SearchProvider):

    def __init__(self):
        self._items = []

    def build_index(self, items: List[Dict[str, Any]]):
        self._items = items
        logger.info("Keyword Search Index ready.")

    def search(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
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

        # Sort by score desc, then by original rank (if avail), then FQN
        matches.sort(key=lambda x: (-x[0], x[1].get("rank", 9999), x[1].get("id", "")))

        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        return matches[start_idx:end_idx]


class HybridSearchProvider(SearchProvider):
    """Tries BM25 first, falls back to Keyword search if zero results found."""

    def __init__(self, bm25: BM25SearchProvider, keyword: KeywordSearchProvider):
        self._bm25 = bm25
        self._keyword = keyword

    def build_index(self, items: List[Dict[str, Any]]):
        self._bm25.build_index(items)
        self._keyword.build_index(items)

    def search(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> List[Tuple[float, Dict[str, Any]]]:
        # Check if BM25 has results globally
        if self._bm25.has_matches(query):
            return self._bm25.search(query, page, page_size)

        logger.info(
            f"BM25 has 0 global results for '{query}'. Falling back to Keyword search."
        )
        return self._keyword.search(query, page, page_size)


def get_search_provider(provider_type: str = "bm25") -> SearchProvider:
    if provider_type == "bm25":
        try:
            import rank_bm25

            return HybridSearchProvider(BM25SearchProvider(), KeywordSearchProvider())
        except ImportError:
            logger.warning("rank_bm25 not found, falling back to keyword search.")
            return KeywordSearchProvider()
    return KeywordSearchProvider()
