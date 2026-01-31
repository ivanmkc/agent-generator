"""Index module."""

import yaml
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from .search import SearchProvider, get_search_provider

logger = logging.getLogger(__name__)


class KnowledgeIndex:

    def __init__(self):
        self._items: List[Dict[str, Any]] = []
        self._fqn_map: Dict[str, Dict[str, Any]] = {}
        self._provider: Optional[SearchProvider] = None
        self._loaded = False

    def load(self, index_path: Path):
        """Loads the index from a YAML file."""
        if self._loaded:
            return

        if not index_path.exists():
            logger.error(f"Index not found at {index_path}")
            return

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self._items = data if isinstance(data, list) else []

                # Sort by rank (ascending)
                self._items.sort(key=lambda x: x.get("rank", 9999))

                self._fqn_map = {}
                for item in self._items:
                    fqn = item.get("id") or item.get("fqn") or item.get("name")
                    if fqn:
                        self._fqn_map[fqn] = item

                # Determine search provider
                api_key = os.environ.get("GEMINI_API_KEY")
                requested_provider = os.environ.get("ADK_SEARCH_PROVIDER", "").lower()
                
                provider_type = "bm25" # Default baseline

                if requested_provider:
                    if requested_provider in ["vector", "hybrid"]:
                        if not api_key:
                            # FAIL FAST if explicitly requested but key is missing
                            raise ValueError(
                                f"ADK_SEARCH_PROVIDER is '{requested_provider}' but GEMINI_API_KEY is missing. "
                                "API key is required for embedding-based search."
                            )
                        provider_type = requested_provider
                    else:
                        provider_type = requested_provider
                else:
                    # Auto-upgrade if key is present
                    if api_key:
                        provider_type = "hybrid"
                        logger.info("GEMINI_API_KEY detected. Auto-upgrading search to 'hybrid'.")
                    else:
                        logger.info("No GEMINI_API_KEY detected. Using 'bm25' search.")

                logger.info(f"Initializing search provider: {provider_type}")
                self._provider = get_search_provider(provider_type)
                self._provider.build_index(self._items)

            self._loaded = True
            logger.info(f"Loaded {len(self._items)} targets from index.")
        except Exception as e:
            # Re-raise ValueErrors (our explicit config failures)
            if isinstance(e, ValueError):
                raise
            logger.error(f"Failed to load index: {e}")

    def resolve_target(self, fqn: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Resolves a FQN to the closest matching item in the index and a suffix path.
        Example: 'a.b.C.m' -> (Item('a.b.C'), 'm')
        """
        if fqn in self._fqn_map:
            return self._fqn_map[fqn], ""

        parts = fqn.split(".")
        for i in range(len(parts) - 1, 0, -1):
            prefix = ".".join(parts[:i])
            if prefix in self._fqn_map:
                suffix = ".".join(parts[i:])
                return self._fqn_map[prefix], suffix

        return None, fqn

    async def search(self, query: str, limit: int = 10) -> List[Tuple[float, Dict[str, Any]]]:
        if not self._provider:
            return []
        # Fix: limit is page_size, page is always 1 for this API
        return await self._provider.search(query, page=1, page_size=limit)

    def list_items(self, page: int, page_size: int) -> List[Dict[str, Any]]:
        start = (page - 1) * page_size
        end = start + page_size
        return self._items[start:end]


# Singleton instance
_global_index = KnowledgeIndex()


def get_index() -> KnowledgeIndex:
    return _global_index
