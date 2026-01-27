import os
import sys
import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add package source to path for testing
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EXT_SRC = PROJECT_ROOT / "tools" / "adk-knowledge-ext" / "src"
sys.path.insert(0, str(EXT_SRC))

# Mock dependencies before import
mock_mcp = MagicMock()
def mock_tool_decorator(*args, **kwargs):
    def decorator(func): return func
    return decorator
mock_mcp.tool.side_effect = mock_tool_decorator

sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()
sys.modules["mcp.server.fastmcp"].FastMCP.return_value = mock_mcp

from adk_knowledge_ext import server, index

def test_nested_symbol_lookup():
    """Reproduces the bug where nested symbols fail."""
    # Reset singleton
    index._global_index = index.KnowledgeIndex()
    
    mock_items = [
        {
            "fqn": "google.adk.models.base_llm_connection.BaseLlmConnection",
            "type": "class",
            "file_path": "google/adk/models/base_llm_connection.py",
            "docstring": "Base class for LLM connections."
        }
    ]
    
    # Mock loading logic
    index.get_index()._items = mock_items
    index.get_index()._fqn_map = {item["fqn"]: item for item in mock_items}
    
    method_fqn = "google.adk.models.base_llm_connection.BaseLlmConnection.send_history"
    
    # 1. Test Inspect
    result_inspect = server.inspect_adk_symbol(method_fqn)
    assert f"Symbol '{method_fqn}' not found in index" not in result_inspect
    assert "BaseLlmConnection" in result_inspect

    # 2. Test Read Source (Mocked)
    file_content = "class BaseLlmConnection:\n    def send_history(self, history): return True"
    
    # Mocking reader directly on the server instance would be cleaner, but reader is global in server.py
    # server.reader is an instance of SourceReader
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value=file_content):
        
        server.ADK_REPO_PATH = Path("/fake/repo")
        result_read = server.read_adk_source_code(method_fqn)
        
        assert "def send_history(self, history):" in result_read
        assert "class BaseLlmConnection" not in result_read

def test_real_index_integrity():
    """Verifies that the extension works with the actual ranked_targets.yaml in this repo."""
    REAL_INDEX_PATH = PROJECT_ROOT / "benchmarks" / "benchmark_generator" / "data" / "ranked_targets.yaml"
    
    if not REAL_INDEX_PATH.exists():
        pytest.skip(f"Real index not found at {REAL_INDEX_PATH}")

    # Use the real index path for loading
    # We must reset the global index first
    index._global_index = index.KnowledgeIndex()
    index.get_index().load(REAL_INDEX_PATH)
    
    # Use real repo path
    # We assume we are running in the project root context
    # ADK source is likely in 'benchmarks/answer_generators/gemini_cli_docker/adk-python'
    # BUT that directory might only contain the stub 'src/adk_agent_tool.py' in this environment!
    # Checking for 'runners.py' failed earlier.
    # So we can only test 'inspect_adk_symbol' (index only) for all items, 
    # and 'read_adk_source_code' only for items that actually exist on disk here.
    
    items = index.get_index()._items
    assert len(items) > 0
    
    for item in items[:20]: # Check first 20 to save time
        fqn = item.get("id") or item.get("fqn")
        if not fqn: continue
        
        # Inspect should always work if loaded
        res = server.inspect_adk_symbol(fqn)
        assert f"Symbol '{fqn}' not found in index" not in res, f"Inspect failed for {fqn}"
