"""Test Adk Knowledge Mcp module."""

import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import yaml
import tempfile
import shutil


# Define a dummy function to substitute run_adk_agent
def dummy_run_adk_agent():
    """Dummy agent runner."""
    pass


# Mock adk_agent_tool before importing adk_knowledge_mcp
mock_adk_agent_tool = MagicMock()
mock_adk_agent_tool.run_adk_agent = dummy_run_adk_agent
sys.modules["adk_agent_tool"] = mock_adk_agent_tool

# Import the module to be tested
# We need to add the directory to sys.path because it's not a package
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

import adk_knowledge_mcp


class TestAdkKnowledgeMcp(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.yaml_path = Path(self.test_dir) / "ranked_targets.yaml"

        # Create sample data
        self.sample_data = [
            {
                "rank": 1,
                "id": "google.adk.runners.InMemoryRunner",
                "name": "InMemoryRunner",
                "type": "CLASS",
                "docstring": "An in-memory Runner for testing.",
            },
            {
                "rank": 2,
                "id": "google.adk.tools.agent_tool.AgentTool",
                "name": "AgentTool",
                "type": "CLASS",
                "docstring": "Tool for agents.",
            },
        ]

        with open(self.yaml_path, "w") as f:
            yaml.dump(self.sample_data, f)

        # Patch the module's path and clear cache
        self.original_path = adk_knowledge_mcp.RANKED_INDEX_PATH
        adk_knowledge_mcp.RANKED_INDEX_PATH = self.yaml_path
        adk_knowledge_mcp._INDEX_CACHE = []
        adk_knowledge_mcp._FQN_MAP = {}

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        adk_knowledge_mcp.RANKED_INDEX_PATH = self.original_path

    def test_list_adk_modules(self):
        # Test listing
        output = adk_knowledge_mcp.list_adk_modules(page=1, page_size=10)

        # Verify it contains the FQNs (which are 'id' in yaml)
        self.assertIn("google.adk.runners.InMemoryRunner", output)
        self.assertIn("google.adk.tools.agent_tool.AgentTool", output)
        self.assertNotIn("unknown", output)
        self.assertIn("[1] CLASS:", output)

    def test_search_adk_knowledge_by_id(self):
        output = adk_knowledge_mcp.search_adk_knowledge("InMemoryRunner")
        self.assertIn("google.adk.runners.InMemoryRunner", output)
        self.assertIn("An in-memory Runner", output)

    def test_search_adk_knowledge_by_docstring(self):
        output = adk_knowledge_mcp.search_adk_knowledge("testing")
        self.assertIn("google.adk.runners.InMemoryRunner", output)

    def test_inspect_adk_symbol_missing_file_path(self):
        # Since our mock data doesn't have file_path, this should return a specific error
        output = adk_knowledge_mcp.inspect_adk_symbol(
            "google.adk.runners.InMemoryRunner"
        )
        self.assertIn("No file path recorded", output)


if __name__ == "__main__":
    unittest.main()
