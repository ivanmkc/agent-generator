import logging
from typing import List, Dict, Any, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class SearchProvider(ABC):
    @abstractmethod
    def build_index(self, items: List[Dict[str, Any]]):
        """Builds the search index from the list of items."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int) -> List[Tuple[float, Dict[str, Any]]]:
        """Searches for the query and returns (score, item) tuples."""
        pass

class BM25SearchProvider(SearchProvider):
    def __init__(self):
        self._bm25_index = None
        self._corpus_map = []  # Maps corpus index to original item index
        self._items = []

    def build_index(self, items: List[Dict[str, Any]]):
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning("rank_bm25 not installed. BM25SearchProvider cannot function.")
            return

        self._items = items
        tokenized_corpus = []
        self._corpus_map = []
        
        for i, item in enumerate(items):
            fqn = item.get("id") or item.get("fqn") or item.get("name")
            if fqn:
                # Create a rich text representation for search
                # FQN gets boosted by repetition
                doc_text = f"{fqn} {fqn} {fqn} " + (item.get("docstring") or "")
                tokenized_corpus.append(doc_text.lower().split())
                self._corpus_map.append(i)

        if tokenized_corpus:
            self._bm25_index = BM25Okapi(tokenized_corpus)
            logger.info(f"BM25 Index built with {len(tokenized_corpus)} items.")

    def search(self, query: str, limit: int) -> List[Tuple[float, Dict[str, Any]]]:
        if not self._bm25_index:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25_index.get_scores(tokenized_query)
        
        # Zip scores with index
        scored_items = []
        for idx, score in enumerate(scores):
            if score > 0:
                scored_items.append((score, idx))
        
        # Sort by score desc
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        matches = []
        top_indices = scored_items[:limit]
        for score, idx in top_indices:
            real_idx = self._corpus_map[idx]
            matches.append((score, self._items[real_idx]))
            
        return matches

class KeywordSearchProvider(SearchProvider):
    def __init__(self):
        self._items = []

    def build_index(self, items: List[Dict[str, Any]]):
        self._items = items
        logger.info("Keyword Search Index ready.")

    def search(self, query: str, limit: int) -> List[Tuple[float, Dict[str, Any]]]:
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
        
        # Sort by score desc, then by original rank
        matches.sort(key=lambda x: (-x[0], x[1].get("rank", 9999)))
        return matches[:limit]

def get_search_provider(provider_type: str = "bm25") -> SearchProvider:
    if provider_type == "bm25":
        try:
            import rank_bm25
            return BM25SearchProvider()
        except ImportError:
            logger.warning("rank_bm25 not found, falling back to keyword search.")
            return KeywordSearchProvider()
    return KeywordSearchProvider()
