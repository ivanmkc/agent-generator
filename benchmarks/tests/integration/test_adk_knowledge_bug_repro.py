import os
import sys
import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

# Setup paths
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(TEST_DIR)))
MCP_DIR = os.path.join(PROJECT_ROOT, "benchmarks", "answer_generators", "gemini_cli_docker", "mcp_adk_agent_runner_ranked_knowledge")
ADK_TOOL_DIR = os.path.join(PROJECT_ROOT, "benchmarks", "answer_generators", "gemini_cli_docker", "adk-python", "src")
REAL_INDEX_PATH = os.path.join(PROJECT_ROOT, "benchmarks", "benchmark_generator", "data", "ranked_targets.yaml")

sys.path.append(MCP_DIR)
sys.path.append(ADK_TOOL_DIR)

# Mock MCP
mock_mcp = MagicMock()
def mock_tool_decorator(*args, **kwargs):
    def decorator(func): return func
    return decorator
mock_mcp.tool.side_effect = mock_tool_decorator

sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()
sys.modules["mcp.server.fastmcp"].FastMCP.return_value = mock_mcp

def test_reproduce_method_lookup_bug():
    """Reproduces the bug where nested symbols fail."""
    import adk_knowledge_mcp
    adk_knowledge_mcp._INDEX_CACHE = []
    adk_knowledge_mcp._FQN_MAP = {}
    
    mock_items = [
        {
            "fqn": "google.adk.models.base_llm_connection.BaseLlmConnection",
            "type": "class",
            "file_path": "google/adk/models/base_llm_connection.py",
            "docstring": "Base class for LLM connections."
        }
    ]
    adk_knowledge_mcp._INDEX_CACHE = mock_items
    adk_knowledge_mcp._FQN_MAP = {item["fqn"]: item for item in mock_items}
    
    method_fqn = "google.adk.models.base_llm_connection.BaseLlmConnection.send_history"
    
    # inspect_adk_symbol should succeed
    result_inspect = adk_knowledge_mcp.inspect_adk_symbol(method_fqn)
    assert f"Symbol '{method_fqn}' not found in index" not in result_inspect
    assert "BaseLlmConnection" in result_inspect

    # read_adk_source_code should succeed and isolate the method
    file_content = "class BaseLlmConnection:\n    def send_history(self, history): return True"
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value=file_content):
        adk_knowledge_mcp.REPO_ROOT = Path("/fake/repo")
        result_read = adk_knowledge_mcp.read_adk_source_code(method_fqn)
        assert "def send_history(self, history):" in result_read
        assert "class BaseLlmConnection" not in result_read


def test_all_top_level_fqns_from_real_index():
    """Iterates over all top-level FQNs in the real ranked_targets.yaml and verifies tool responses."""
    import adk_knowledge_mcp
    
    if not os.path.exists(REAL_INDEX_PATH):
        pytest.skip(f"Real index not found at {REAL_INDEX_PATH}")

    with open(REAL_INDEX_PATH, "r") as f:
        real_items = yaml.safe_load(f)

    # Initialize the module's maps with real data
    adk_knowledge_mcp._INDEX_CACHE = real_items
    adk_knowledge_mcp._FQN_MAP = {item.get("id") or item.get("fqn"): item for item in real_items}
    
    # We set REPO_ROOT to the actual path where adk-python is located
    # In this environment, it's typically benchmarks/answer_generators/gemini_cli_docker/adk-python
    real_repo_root = Path(ADK_TOOL_DIR).parent
    adk_knowledge_mcp.REPO_ROOT = real_repo_root

    # We do NOT patch Path.exists or Path.read_text. We use the real file system.
    # This ensures that every file path in the index actually exists and is readable/parsable.
    
    for item in real_items:
        fqn = item.get("id") or item.get("fqn")
        if not fqn: continue
        
        # 1. Test inspect_adk_symbol
        inspect_res = adk_knowledge_mcp.inspect_adk_symbol(fqn)
        assert f"Symbol '{fqn}' not found in index" not in inspect_res, f"Inspect failed for {fqn}"
        
        # 2. Test read_adk_source_code
        read_res = adk_knowledge_mcp.read_adk_source_code(fqn)
        
        # Check for various failure modes
        assert f"Symbol '{fqn}' not found in index" not in read_res, f"Read source failed for {fqn} (index error)"
        
        # Only assert isolation success if the tool claims it found the file
        # Some symbols might be aliases or dynamic, so isolation failure isn't always a hard bug for every single FQN,
        # but for the core classes it should work.
        # Let's verify we at least found the file.
        assert "File not found on disk" not in read_res, f"File missing for {fqn} (Path: {item.get('file_path')})"
        assert "Error reading file" not in read_res, f"Error parsing/reading file for {fqn}: {read_res}"
        
        # Verify isolation success
        if "Symbol isolation failed" in read_res:
            # Optionally print warning or fail if strict
            # For this test, let's fail to ensure high quality
            pytest.fail(f"Failed to isolate AST for {fqn} in {item.get('file_path')}")
            
        assert f"=== Source: {fqn} ===" in read_res
