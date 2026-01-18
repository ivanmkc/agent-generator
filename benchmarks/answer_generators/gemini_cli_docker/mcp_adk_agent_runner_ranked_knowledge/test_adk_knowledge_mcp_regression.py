
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import yaml
import tempfile

# Add the module path to sys.path
module_path = Path(__file__).parent
sys.path.append(str(module_path))

# --- Mock Setup ---
# We need a mock that behaves like a decorator: @mcp.tool()
def passthrough_decorator(func=None, **kwargs):
    if func and callable(func):
        return func
    def actual_decorator(f):
        return f
    return actual_decorator

mock_mcp_class = MagicMock()
mock_instance = MagicMock()
mock_instance.tool.side_effect = passthrough_decorator
mock_mcp_class.return_value = mock_instance

sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()
sys.modules["mcp.server.fastmcp"].FastMCP = mock_mcp_class
sys.modules["adk_agent_tool"] = MagicMock()

# --- Import ---
if "adk_knowledge_mcp" in sys.modules:
    del sys.modules["adk_knowledge_mcp"]
import adk_knowledge_mcp

class TestAdkKnowledgeMcp:

    @pytest.fixture
    def mock_yaml_file(self):
        # Create a temp file with various data shapes to test robustness
        data = [
            # Item with 'id' (Standard)
            {
                "rank": 1,
                "id": "google.adk.Standard",
                "type": "CLASS",
                "docstring": "Standard item"
            },
            # Item with 'fqn' but no 'id' (Legacy/Fallback)
            {
                "rank": 2,
                "fqn": "google.adk.FallbackFQN",
                "type": "CLASS",
                "docstring": "Fallback item FQN"
            },
            # Item with 'name' but no 'id' or 'fqn' (Last resort)
            {
                "rank": 3,
                "name": "google.adk.FallbackName",
                "type": "CLASS",
                "docstring": "Fallback item Name"
            },
            # Item with nothing
            {
                "rank": 4,
                "type": "CLASS",
                "docstring": "Unknown item"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(data, f)
            path = Path(f.name)
            
        yield path
        
        if path.exists():
            path.unlink()

    def test_list_adk_modules_robustness(self, mock_yaml_file):
        """Verify list_adk_modules handles missing ID fields gracefully."""
        with patch("adk_knowledge_mcp.RANKED_INDEX_PATH", mock_yaml_file):
            # Reset cache
            adk_knowledge_mcp._INDEX_CACHE = []
            
            result = adk_knowledge_mcp.list_adk_modules(page=1, page_size=10)
            
            print(f"Result:\n{result}")
            
            assert "google.adk.Standard" in result
            assert "google.adk.FallbackFQN" in result
            assert "google.adk.FallbackName" in result
            assert "unknown" in result # For the 4th item

    def test_search_adk_knowledge_robustness(self, mock_yaml_file):
        """Verify search_adk_knowledge finds items even with fallback keys."""
        with patch("adk_knowledge_mcp.RANKED_INDEX_PATH", mock_yaml_file):
            adk_knowledge_mcp._INDEX_CACHE = []
            
            # Search for FQN
            result = adk_knowledge_mcp.search_adk_knowledge("FallbackFQN", limit=5)
            assert "google.adk.FallbackFQN" in result
            
            # Search for Name
            result = adk_knowledge_mcp.search_adk_knowledge("FallbackName", limit=5)
            assert "google.adk.FallbackName" in result

    def test_inspect_adk_symbol_robustness(self, mock_yaml_file):
        """Verify inspect_adk_symbol can look up items indexed by fallback keys."""
        with patch("adk_knowledge_mcp.RANKED_INDEX_PATH", mock_yaml_file):
            adk_knowledge_mcp._INDEX_CACHE = []
            adk_knowledge_mcp._FQN_MAP = {} # Ensure map is rebuilt
            
            # Helper to mock REPO_ROOT and file reading since we don't have real files
            with patch("adk_knowledge_mcp.REPO_ROOT", Path("/tmp")):
                 with patch("pathlib.Path.exists", return_value=True):
                      with patch("pathlib.Path.read_text", return_value="source code"):
                        
                        # Trigger load
                        adk_knowledge_mcp._load_index()
                        
                        # Verify Map population
                        assert "google.adk.Standard" in adk_knowledge_mcp._FQN_MAP
                        assert "google.adk.FallbackFQN" in adk_knowledge_mcp._FQN_MAP
                        assert "google.adk.FallbackName" in adk_knowledge_mcp._FQN_MAP

if __name__ == "__main__":
    # Manually run if executed as script
    t = TestAdkKnowledgeMcp()
    # Need to simulate fixture
    data = [
        # Item with 'id' (Standard)
        {
            "rank": 1,
            "id": "google.adk.Standard",
            "type": "CLASS",
            "docstring": "Standard item"
        },
        # Item with 'fqn' but no 'id' (Legacy/Fallback)
        {
            "rank": 2,
            "fqn": "google.adk.FallbackFQN",
            "type": "CLASS",
            "docstring": "Fallback item FQN"
        },
        # Item with 'name' but no 'id' or 'fqn' (Last resort)
        {
            "rank": 3,
            "name": "google.adk.FallbackName",
            "type": "CLASS",
            "docstring": "Fallback item Name"
        },
        # Item with nothing
        {
            "rank": 4,
            "type": "CLASS",
            "docstring": "Unknown item"
        }
    ]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(data, f)
        p = Path(f.name)
    
    try:
        t.test_list_adk_modules_robustness(p)
        t.test_search_adk_knowledge_robustness(p)
        # Mocking for inspect_adk_symbol is complex in main block, relying on pytest for that
        print("All Manual Tests Passed (list/search)")
    finally:
        p.unlink()
