import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add the directory containing the MCP module to the path
# Current file: benchmarks/tests/integration/test_adk_knowledge_mcp.py
# Target: benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner_ranked_knowledge
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BENCHMARKS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(TEST_DIR)))
MCP_DIR = os.path.join(BENCHMARKS_DIR, "benchmarks", "answer_generators", "gemini_cli_docker", "mcp_adk_agent_runner_ranked_knowledge")
sys.path.append(MCP_DIR)

# Mock dependencies that might be missing or troublesome in the test environment
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()
sys.modules["adk_agent_tool"] = MagicMock()

# Mock rank_bm25 if not installed, but we want to test the selection logic
sys.modules["rank_bm25"] = MagicMock()

def test_search_provider_selection_bm25_default():
    """Test that BM25 is selected by default if available."""
    with patch.dict(os.environ, {}, clear=True):
        # We need to reload the module to trigger the top-level logic or specifically the _get_search_provider logic
        # However, _get_search_provider uses a global variable. We should reset it.
        import adk_knowledge_mcp
        adk_knowledge_mcp._SEARCH_PROVIDER = None
        adk_knowledge_mcp.SEARCH_PROVIDER_TYPE = "bm25"
        adk_knowledge_mcp.HAS_BM25 = True
        
        provider = adk_knowledge_mcp._get_search_provider()
        assert isinstance(provider, adk_knowledge_mcp.BM25SearchProvider)

def test_search_provider_selection_keyword_explicit():
    """Test that Keyword provider is selected when env var is set."""
    # We patch os.environ but since the module reads it at import time, we must manually override the global
    import adk_knowledge_mcp
    adk_knowledge_mcp._SEARCH_PROVIDER = None
    adk_knowledge_mcp.SEARCH_PROVIDER_TYPE = "keyword"
    
    provider = adk_knowledge_mcp._get_search_provider()
    assert isinstance(provider, adk_knowledge_mcp.KeywordSearchProvider)

def test_search_provider_fallback_when_bm25_missing():
    """Test fallback to Keyword if BM25 is requested but missing."""
    import adk_knowledge_mcp
    adk_knowledge_mcp._SEARCH_PROVIDER = None
    adk_knowledge_mcp.SEARCH_PROVIDER_TYPE = "bm25"
    adk_knowledge_mcp.HAS_BM25 = False
    
    provider = adk_knowledge_mcp._get_search_provider()
    # It should log a warning and return KeywordSearchProvider
    assert isinstance(provider, adk_knowledge_mcp.KeywordSearchProvider)

def test_bm25_provider_build_and_search():
    """Test that BM25 provider builds index and returns results."""
    import adk_knowledge_mcp
    adk_knowledge_mcp.HAS_BM25 = True
    provider = adk_knowledge_mcp.BM25SearchProvider()
    
    # Mock data
    items = [
        {"fqn": "foo.bar", "docstring": "helper function"},
        {"fqn": "baz.qux", "docstring": "main controller"},
    ]
    
    # Mock BM25Okapi instance
    mock_bm25 = MagicMock()
    # Return scores: first item (foo.bar) matches better
    mock_bm25.get_scores.return_value = [10.0, 1.0] 
    
    with patch("adk_knowledge_mcp.BM25Okapi", return_value=mock_bm25):
        provider.build_index(items)
        results = provider.search("helper", 10)
        
        assert len(results) == 2
        assert results[0][1]["fqn"] == "foo.bar"
        assert results[0][0] == 10.0

def test_keyword_provider_search():
    """Test that Keyword provider filters and scores correctly."""
    import adk_knowledge_mcp
    provider = adk_knowledge_mcp.KeywordSearchProvider()
    
    items = [
        {"fqn": "foo.bar", "docstring": "unrelated"},
        {"fqn": "baz.target", "docstring": "this is the target"},
    ]
    provider.build_index(items)
    
    results = provider.search("target", 10)
    
    assert len(results) == 1
    assert results[0][1]["fqn"] == "baz.target"
    # Score details: "target" is in fqn (10) + endswith (20) = 30?
    # actually "baz.target" ends with "target" so +20. "target" in "baz.target" +10.
    # "target" also in docstring? No.
    # Let's check logic:
    # kw in fqn: +10.
    # fqn.endswith("." + kw) -> ".target" yes. +20.
    # Total 30.
    assert results[0][0] >= 30
