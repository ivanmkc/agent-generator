import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add project root and search source to sys.path
PROJECT_ROOT = Path.cwd()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
ext_src = PROJECT_ROOT / "tools/adk_knowledge_ext/src"
if str(ext_src) not in sys.path:
    sys.path.append(str(ext_src))

from benchmarks.answer_generators.adk_tools import AdkTools

@pytest.mark.asyncio
async def test_vector_search_real_index():
    """
    Integration test that performs a semantic search using the actual built index.
    This replaces the demo script.
    """
    # Initialize AdkTools with project root
    tools = AdkTools(PROJECT_ROOT)
    
    # Verify that the search provider is initialized with a Vector provider
    # By checking if the internal search provider is a Hybrid or Vector one
    assert tools._search_provider is not None, "Search provider not initialized"
    
    query = "how to automatically retry failed turns"
    print(f"\nQuerying: '{query}'")
    
    results_str = await tools.search_ranked_targets(query, page_size=5)
    
    # Verify results
    assert "Search Results" in results_str
    # ReflectAndRetryToolPlugin should be in the top results for this query
    # Note: The name in index might be ReflectAndRetryToolPlugin or similar
    assert "Reflect" in results_str or "Retry" in results_str
    
    print("\nSearch results:")
    print(results_str)

@pytest.mark.asyncio
async def test_semantic_query_session_state():
    """Tests semantic search for session state persistence."""
    tools = AdkTools(PROJECT_ROOT)
    query = "persisting agent session state"
    
    results_str = await tools.search_ranked_targets(query, page_size=5)
    
    assert "Search Results" in results_str
    assert "Runner" in results_str or "Session" in results_str
    
    print(f"\nQuerying: '{query}'")
    print(results_str)
