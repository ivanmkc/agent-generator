import unittest
from adk_knowledge_ext.search import BM25SearchProvider

class TestBM25Search(unittest.TestCase):
    def test_search_fqn_suffix(self):
        items = [
            {"id": "google.adk.tools.ToolConfig", "docstring": "Configuration for tools."},
            {"id": "google.adk.agents.LlmAgent", "docstring": "LLM Agent."},
            {"id": "google.adk.other.Thing", "docstring": "Something else."} # Dummy to fix IDF
        ]
        provider = BM25SearchProvider()
        provider.build_index(items)
        
        results = provider.search("ToolConfig", limit=1)
        print(f"Results for 'ToolConfig': {results}")
        self.assertTrue(len(results) > 0, "Should find ToolConfig")
        self.assertEqual(results[0][1]["id"], "google.adk.tools.ToolConfig")

if __name__ == '__main__':
    unittest.main()
