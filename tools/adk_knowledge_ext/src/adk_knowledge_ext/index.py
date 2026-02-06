"""Index module."""

import yaml
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from .search import (
    SearchProvider,
    get_search_provider,
)
from .config import config

logger = logging.getLogger(__name__)


def _initialize_search_provider(
    requested_provider: str, api_key: Optional[str], embeddings_path: Optional[Path]
) -> SearchProvider:
    """Helper to determine and instantiate the correct SearchProvider using the registry."""
    provider_type = "bm25"  # Default baseline

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
    
    # Use the registry factory
    return get_search_provider(provider_type, index_dir=embeddings_path, api_key=api_key)


class KnowledgeIndex:

    def __init__(self):
        self._items: List[Dict[str, Any]] = []
        self._fqn_map: Dict[str, Dict[str, Any]] = {}
        self._provider: Optional[SearchProvider] = None
        self._loaded = False

    def load(self, index_path: Path):
        """Loads the index from a YAML file."""
        # TODO: Implement on-demand/lazy loading for large indices to reduce startup latency
        # and memory footprint. Consider using a disk-backed store (e.g., SQLite) or 
        # chunked loading.
        if self._loaded:
            return

        if not index_path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")

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
                embeddings_path = config.EMBEDDINGS_FOLDER_PATH
                if not embeddings_path:
                    # Heuristic: look for vectors in the same directory as index
                    if (index_path.parent / "targets_vectors.npy").exists():
                        embeddings_path = index_path.parent
                        logger.info(f"Auto-detected embeddings folder: {embeddings_path}")

                self._provider = _initialize_search_provider(
                    config.ADK_SEARCH_PROVIDER.lower(),
                    config.GEMINI_API_KEY,
                    embeddings_path,
                )
                self._provider.build_index(self._items)

            self._loaded = True
            logger.info(f"Loaded {len(self._items)} targets from index.")
        except Exception as e:
            # Re-raise ValueErrors (our explicit config failures)
            if isinstance(e, ValueError):
                raise
            logger.error(f"Failed to load index: {e}")
            # Ensure we don't proceed with partial/broken load
            raise

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


# Singleton instances
_registry = None


class KnowledgeRegistry:
    def __init__(self):
        self._indices: Dict[str, KnowledgeIndex] = {}

    def get_index(self, kb_id: str) -> KnowledgeIndex:
        """Returns the KnowledgeIndex for the given ID, creating it if needed."""
        if kb_id not in self._indices:
            self._indices[kb_id] = KnowledgeIndex()
        return self._indices[kb_id]

    def list_available_kb_ids(self) -> List[str]:
        return list(self._indices.keys())


def get_registry() -> KnowledgeRegistry:
    global _registry
    if _registry is None:
        _registry = KnowledgeRegistry()
    return _registry


def get_index(kb_id: Optional[str] = None) -> KnowledgeIndex:
    """
    Deprecated: Use get_registry().get_index(kb_id) instead.
    Provided for backward compatibility during transition.
    """
    if kb_id is None:
        # Fallback to a default if not provided (for existing tools not yet updated)
        kb_id = "default"
    return get_registry().get_index(kb_id)