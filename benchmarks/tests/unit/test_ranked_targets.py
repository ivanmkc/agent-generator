import unittest
from pathlib import Path
from unittest.mock import patch, mock_open
import yaml
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.benchmark_generator.models import RankedTarget

class TestRankedTargets(unittest.TestCase):
    def setUp(self):
        self.workspace_root = Path("/tmp/workspace")
        self.adk_tools = AdkTools(self.workspace_root)
        
        self.mock_yaml_content = """
- rank: 1
  id: google.adk.MockClass
  name: MockClass
  type: CLASS
  group: Seed
  usage_score: 100
  docstring: "A mock class for testing."
  methods:
    - signature: "def mock_method(self):"
      docstring: "A mock method."
  properties:
    - signature: "mock_prop: int"
      docstring: "A mock property."
  inherited_methods:
    BaseClass:
      - signature: "def base_method(self):"
        docstring: "Inherited method."
"""
        self.mock_data = yaml.safe_load(self.mock_yaml_content)

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    @patch("pathlib.Path.exists")
    def test_list_ranked_targets(self, mock_exists, mock_yaml_load, mock_file):
        # Setup mocks
        mock_exists.return_value = True
        mock_yaml_load.return_value = self.mock_data
        
        # Execute
        output = self.adk_tools.list_ranked_targets(page=1, page_size=10)
        
        # Verify
        self.assertIn("--- Ranked Targets (Page 1 of 1) ---", output)
        self.assertIn("[1] google.adk.MockClass: A mock class for testing.", output)

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    @patch("pathlib.Path.exists")
    def test_search_ranked_targets(self, mock_exists, mock_yaml_load, mock_file):
        # Setup mocks
        mock_exists.return_value = True
        mock_yaml_load.return_value = self.mock_data

        # Execute - Match found
        output = self.adk_tools.search_ranked_targets("MockClass")
        self.assertIn("--- Search Results for 'mockclass'", output)
        self.assertIn("[1] google.adk.MockClass", output)

        # Execute - No match
        output_fail = self.adk_tools.search_ranked_targets("NonExistent")
        self.assertIn("No targets found matching: nonexistent", output_fail)

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    @patch("pathlib.Path.exists")
    def test_inspect_ranked_target(self, mock_exists, mock_yaml_load, mock_file):
        # Setup mocks
        mock_exists.return_value = True
        mock_yaml_load.return_value = self.mock_data

        # Execute
        output = self.adk_tools.inspect_ranked_target("google.adk.MockClass")

        # Verify
        self.assertIn("=== Inspection: google.adk.MockClass ===", output)
        self.assertIn("Type: CLASS", output)
        self.assertIn("Rank: 1", output)
        self.assertIn("[Docstring]", output)
        self.assertIn("A mock class for testing.", output)
        self.assertIn("[Methods]", output)
        self.assertIn("- def mock_method(self):", output)
        self.assertIn("[Properties]", output)
        self.assertIn("- mock_prop: int", output)
        self.assertIn("[Inherited Methods]", output)
        self.assertIn("From BaseClass:", output)
        self.assertIn("- def base_method(self):", output)

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    @patch("pathlib.Path.exists")
    def test_inspect_ranked_target_not_found(self, mock_exists, mock_yaml_load, mock_file):
        # Setup mocks
        mock_exists.return_value = True
        mock_yaml_load.return_value = self.mock_data

        # Execute
        output = self.adk_tools.inspect_ranked_target("google.adk.Unknown")

        # Verify
        self.assertIn("Target 'google.adk.Unknown' not found in ranked index.", output)

if __name__ == "__main__":
    unittest.main()
