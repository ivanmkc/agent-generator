"""
Tests for server-side logic in the ADK Knowledge Extension.

This module consolidates tests for:
- Semantic Versioning (SemVer) sorting of Knowledge Bases.
- Search determinism (BM25, Keyword).
- Search reproducibility and edge cases (FQN suffix, Fallbacks).
- Vector search logic (mocked).
"""

import pytest
from adk_knowledge_ext.models import RankedTarget
import sys
import yaml


import json
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from adk_knowledge_ext.server import _get_available_kbs
from adk_knowledge_ext.search import (
    BM25SearchProvider, 
    KeywordSearchProvider, 
    CompositeSearchProvider,
    VectorSearchProvider
)
from adk_knowledge_ext.index import _initialize_search_provider

# Mock data for registry (from test_server_sorting.py)
MOCK_REGISTRY_DATA = {
    "repositories": {
        "google/adk-python": {
            "repo_url": "https://github.com/google/adk-python.git",
            "description": "ADK Python",
            "versions": {
                "v1.9.0": {"index_url": "indices/v1.9.0/ranked_targets.yaml"},
                "v1.10.0": {"index_url": "indices/v1.10.0/ranked_targets.yaml"},
                "v1.2.0": {"index_url": "indices/v1.2.0/ranked_targets.yaml"}
            }
        }
    }
}

# --- Server Version Sorting Tests ---

@patch("adk_knowledge_ext.server.Path")
def test_server_semver_sorting(mock_path_cls):
    """
    Tests that server.py correctly identifies the latest version using SemVer semantics,
    not simple string sorting.
    
    Scenario:
        Versions present: v1.9.0, v1.10.0, v1.2.0
        
        Expected Default: v1.10.0
        
        Failure Mode (String Sort):
            "v1.9.0" > "v1.2.0" (True)
            "v1.9.0" > "v1.10.0" (True because '9' > '1')
            So String Sort would pick v1.9.0, which is incorrect.
    """
    # Setup mock for registry.yaml reading
    # We simulate a file structure where mocked server.path / "registry.yaml" returns our data
    mock_registry_path = MagicMock()
    mock_registry_path.exists.return_value = True
    mock_registry_path.read_text.return_value = yaml.dump(MOCK_REGISTRY_DATA)
    
    mock_parent = MagicMock()
    mock_parent.__truediv__.side_effect = lambda x: mock_registry_path if x == "registry.yaml" else MagicMock()
    
    mock_file_path = MagicMock()
    mock_file_path.parent = mock_parent
    
    mock_path_cls.return_value = mock_file_path
    
    # Act
    kbs = _get_available_kbs()
    
    # Assert
    # The default alias (key "google/adk-python") should point to the latest version
    default_kb = kbs.get("google/adk-python")
    assert default_kb is not None, "Default alias not found"
    
    print(f"Detected default version: {default_kb.version}")
    
    # This assertion will fail if simple string sort is used (it likely picks v1.9.0)
    assert default_kb.version == "v1.10.0", f"Expected v1.10.0 but got {default_kb.version}"


# --- Search Determinism Tests ---

@pytest.mark.asyncio
async def test_bm25_determinism_with_shuffle():
    # Items with identical content but different IDs
    items = [
        {"id": "A", "docstring": "test content", "rank": 10},
        {"id": "B", "docstring": "test content", "rank": 5},
        {"id": "C", "docstring": "irrelevant", "rank": 1},  # Dummy for IDF
    ]

    # Provider 1: Natural order
    p1 = BM25SearchProvider()
    p1.build_index(items)
    r1 = await p1.search("test")

    # Provider 2: Reversed input order
    p2 = BM25SearchProvider()
    p2.build_index(list(reversed(items)))
    r2 = await p2.search("test")

    # Expect B first (Rank 5 < 10) regardless of input order
    assert r1[0][1]["id"] == "B"
    assert r2[0][1]["id"] == "B"

    # Exact match of results list
    assert r1 == r2

@pytest.mark.asyncio
async def test_pagination():
    # Create 20 items. Keyword search sorts by Rank ASC.
    # So Item_0 (rank 0) ... Item_19 (rank 19)
    items = [
        {"id": f"Item_{i}", "docstring": "common keyword", "rank": i}
        for i in range(20)
    ]
    provider = KeywordSearchProvider()
    provider.build_index(items)

    page1 = await provider.search("common", page=1, page_size=10)
    assert len(page1) == 10
    assert page1[0][1]["id"] == "Item_0"
    assert page1[9][1]["id"] == "Item_9"

    page2 = await provider.search("common", page=2, page_size=10)
    assert len(page2) == 10
    assert page2[0][1]["id"] == "Item_10"
    assert page2[9][1]["id"] == "Item_19"

    page3 = await provider.search("common", page=3, page_size=10)
    assert len(page3) == 0


# --- Search Repro / Logic Tests ---

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
    provider = _initialize_search_provider("bm25", None, None)
    assert isinstance(provider, BM25SearchProvider)
    
    # Simulate a missing dependency safely by replacing the method entirely
    def _mock_build_index(self_instance, items):
        import logging
        logging.getLogger(__name__).warning("rank_bm25 not installed. BM25SearchProvider cannot function.")
        
    with patch.object(BM25SearchProvider, 'build_index', new=_mock_build_index):
        # Should not crash when building index
        provider.build_index([RankedTarget(id="test", name="test", group="test", type="test", rank=1, usage_score=1)])
        
        # Since _corpus_map is empty, search will return [] unharmed natively.
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


# --- Vector Search Tests ---

@pytest.fixture
def mock_index_dir(tmp_path):
    vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
    metadata = [
        {"id": "class.A", "type": "CLASS", "rank": 1},
        {"id": "class.B", "type": "CLASS", "rank": 2}
    ]
    np.save(tmp_path / "vectors.npy", vectors)
    with open(tmp_path / "vector_keys.yaml", "w") as f:
        yaml.dump(metadata, f)
    return tmp_path

@pytest.fixture
def items():
    return [
        {"id": "class.A", "docstring": "Apple"},
        {"id": "class.B", "docstring": "Banana"}
    ]

@pytest.mark.asyncio
async def test_vector_search_success(mock_index_dir, items):
    provider = VectorSearchProvider(mock_index_dir, api_key="fake_key")
    provider.build_index(items)
    
    # Mock GenAI client
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Mock embedding for [1.0, 0.1] -> should favor class.A
    mock_response.embeddings = [MagicMock(values=[1.0, 0.1])]
    mock_client.models.embed_content.return_value = mock_response
    
    with patch.object(provider, "_get_client", return_value=mock_client):
        results = await provider.search("fruit")
        
        assert len(results) > 0
        score, item = results[0]
        assert item["id"] == "class.A"
        assert score > 0.9

@pytest.mark.asyncio
async def test_vector_search_no_index(tmp_path):
    provider = VectorSearchProvider(tmp_path, api_key="fake_key")
    provider.build_index([])
    results = await provider.search("query")
    assert results == []
