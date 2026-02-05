"""Test Search Repro module."""

import pytest
import sys
from unittest.mock import patch
from adk_knowledge_ext.search import BM25SearchProvider, KeywordSearchProvider, CompositeSearchProvider
from adk_knowledge_ext.index import _initialize_search_provider

@pytest.mark.asyncio
async def test_search_fqn_suffix():
    items = [
        {
            "id": "google.adk.tools.ToolConfig",
            "docstring": "Configuration for tools.",
        },
        {"id": "google.adk.agents.LlmAgent", "docstring": "LLM Agent."},
        {
            "id": "google.adk.other.Thing",
            "docstring": "Something else.",
        },  # Dummy to fix IDF
    ]
    provider = BM25SearchProvider()
    provider.build_index(items)

    results = await provider.search("ToolConfig", page=1, page_size=1)
    print(f"Results for 'ToolConfig': {results}")
    assert len(results) > 0, "Should find ToolConfig"
    assert results[0][1]["id"] == "google.adk.tools.ToolConfig"

@pytest.mark.asyncio
async def test_bm25_fallback_to_keyword():
    """Verifies that BM25SearchProvider handles missing rank_bm25 gracefully (logs warning, doesn't crash)."""
    with patch.dict(sys.modules, {"rank_bm25": None}):
        provider = _initialize_search_provider("bm25", None, None)
        assert isinstance(provider, BM25SearchProvider)
        
        # Should not crash when building index
        provider.build_index([{"id": "test"}])
        
        # Should return empty results or not crash
        results = await provider.search("test")
        assert len(results) == 0

@pytest.mark.asyncio
async def test_hybrid_search_cascading_fallback():
    """Verifies that CompositeSearchProvider falls back to keyword if BM25 finds nothing."""
    # Create a scenario where BM25 score would be 0 (small N, 50% frequency)
    # but keyword search will still find it.
    items = [
        {
            "id": "google.adk.tools.ToolConfig",
            "docstring": "Configuration for tools.",
        },
        {"id": "google.adk.agents.LlmAgent", "docstring": "LLM Agent."},
    ]

    # We manually construct Composite to isolate logic
    from adk_knowledge_ext.search import CompositeSearchProvider

    provider = CompositeSearchProvider([BM25SearchProvider(), KeywordSearchProvider()])
    provider.build_index(items)

    # 'ToolConfig' appears in 1/2 docs, so BM25 score is 0.0 (as seen in repro)
    # But Keyword search should find it by substring matching.
    results = await provider.search("ToolConfig", page=1, page_size=1)

    assert len(results) > 0, "Hybrid search should find ToolConfig via Keyword fallback"
    assert results[0][1]["id"] == "google.adk.tools.ToolConfig"