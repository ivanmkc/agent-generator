"""Test Integration module."""

import os
import sys
import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add package source to path for testing
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EXT_SRC = PROJECT_ROOT / "tools" / "adk_knowledge_ext" / "src"
sys.path.insert(0, str(EXT_SRC))

# Mock dependencies before import
mock_mcp = MagicMock()


def mock_tool_decorator(*args, **kwargs):
    def decorator(func):
        return func

    return decorator


mock_mcp.tool.side_effect = mock_tool_decorator

# Apply patches to sys.modules specifically for the import of adk_knowledge_ext
# This prevents polluting sys.modules for subsequent tests that need the real 'mcp'
with patch.dict(sys.modules, {
    "mcp": MagicMock(),
    "mcp.server": MagicMock(),
    "mcp.server.fastmcp": MagicMock(),
}):
    # Configure the mock return value
    sys.modules["mcp.server.fastmcp"].FastMCP.return_value = mock_mcp
    
    # Import the modules under test
    from adk_knowledge_ext import server, index

# At this point, sys.modules is restored (mcp is removed), 
# but 'server' and 'index' variables still point to the loaded modules 
# which hold references to the mocks. This is what we want.


def test_nested_symbol_lookup():
    """Reproduces the bug where nested symbols fail."""
    # Reset singleton
    index._global_index = index.KnowledgeIndex()

    mock_items = [
        {
            "fqn": "google.adk.models.base_llm_connection.BaseLlmConnection",
            "type": "class",
            "file_path": "google/adk/models/base_llm_connection.py",
            "docstring": "Base class for LLM connections.",
        }
    ]

    # Mock loading logic
    index.get_index()._items = mock_items
    index.get_index()._fqn_map = {item["fqn"]: item for item in mock_items}

    method_fqn = "google.adk.models.base_llm_connection.BaseLlmConnection.send_history"

    # 1. Test Inspect
    # We must patch _ensure_index because it validates env vars which are missing here
    with patch.object(server, "_ensure_index"):
        result_inspect = server.inspect_symbol(method_fqn)
        assert f"Symbol '{method_fqn}' not found in index" not in result_inspect
        assert "BaseLlmConnection" in result_inspect

    # 2. Test Read Source (Mocked)
    expected_source = "class BaseLlmConnection:\n    def send_history(self, history): return True"

    # Mock reader.read_source to bypass disk operations and git cloning
    # We need to patch reader on the server object instance
    with patch.object(server.reader, "read_source", return_value=expected_source), \
         patch.object(server, "_ensure_index"):

        result_read = server.read_source_code(method_fqn)

        assert "def send_history(self, history):" in result_read
        assert "class BaseLlmConnection" in result_read # Should match the return value



def test_real_index_integrity():
    """Verifies that the extension works with the actual ranked_targets.yaml in this repo."""
    REAL_INDEX_PATH = (
        PROJECT_ROOT
        / "benchmarks"
        / "generator"
        / "benchmark_generator"
        / "data"
        / "ranked_targets.yaml"
    )

    if not REAL_INDEX_PATH.exists():
        pytest.skip(f"Real index not found at {REAL_INDEX_PATH}")

    # Configure environment to make _ensure_index happy and load the correct file
    os.environ["TARGET_REPO_URL"] = "https://github.com/google/adk-python.git"
    os.environ["TARGET_VERSION"] = "v1.20.0" # Dummy
    os.environ["TARGET_INDEX_PATH"] = str(REAL_INDEX_PATH)
    
    # Reload config to pick up env vars (config object is instantiated on import)
    # We can just manually set the property cache or re-import?
    # config uses @property so it reads os.environ on every access.
    
    # We assume server._ensure_index will call config.TARGET_INDEX_PATH -> os.getenv -> find our path -> load it.
    # But wait, index is a singleton. _ensure_index loads it.
    # So we don't need to manually load it if we set the env var correctly!
    
    # Reset singleton just in case
    index._global_index = index.KnowledgeIndex()

    # Use real repo path
    # We assume we are running in the project root context
    # ADK source is likely in 'benchmarks/answer_generators/gemini_cli_docker/adk-python'
    # BUT that directory might only contain the stub 'src/adk_agent_tool.py' in this environment!
    # Checking for 'runners.py' failed earlier.
    # So we can only test 'inspect_symbol' (index only) for all items,
    # and 'read_source_code' only for items that actually exist on disk here.
    
    # Manually trigger load to get items for iteration
    # (server tools call _ensure_index internally, but we need items list here)
    index.get_index().load(REAL_INDEX_PATH)

    items = index.get_index()._items
    assert len(items) > 0

    for item in items[:20]:  # Check first 20 to save time
        fqn = item.get("id") or item.get("fqn")
        if not fqn:
            continue

        # Inspect should always work if loaded
        res = server.inspect_symbol(fqn)
        assert (
            f"Symbol '{fqn}' not found in index" not in res
        ), f"Inspect failed for {fqn}"
