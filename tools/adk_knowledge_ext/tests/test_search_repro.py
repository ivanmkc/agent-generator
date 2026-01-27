"""Test Search Repro module."""

import unittest
import sys
from unittest.mock import patch
from adk_knowledge_ext.search import BM25SearchProvider, get_search_provider, KeywordSearchProvider, HybridSearchProvider


class TestBM25Search(unittest.TestCase):

    def test_search_fqn_suffix(self):
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

        results = provider.search("ToolConfig", page=1, page_size=1)
        print(f"Results for 'ToolConfig': {results}")
        self.assertTrue(len(results) > 0, "Should find ToolConfig")
        self.assertEqual(results[0][1]["id"], "google.adk.tools.ToolConfig")

    def test_bm25_fallback_to_keyword(self):
        """Verifies that get_search_provider falls back to KeywordSearchProvider if rank_bm25 is missing."""
        with patch.dict(sys.modules, {"rank_bm25": None}):
            # We need to reload or ensure the import inside get_search_provider triggers the ImportError
            # Since get_search_provider has the import inside the function (local import), patching sys.modules works.
            provider = get_search_provider("bm25")
            self.assertIsInstance(
                provider,
                (KeywordSearchProvider, HybridSearchProvider),
                "Should fallback gracefully",
            )

    def test_hybrid_search_cascading_fallback(self):
        """Verifies that HybridSearchProvider falls back to keyword if BM25 finds nothing."""
        # Create a scenario where BM25 score would be 0 (small N, 50% frequency)
        # but keyword search will still find it.
        items = [
            {
                "id": "google.adk.tools.ToolConfig",
                "docstring": "Configuration for tools.",
            },
            {"id": "google.adk.agents.LlmAgent", "docstring": "LLM Agent."},
        ]

        # We manually construct Hybrid to isolate logic
        from adk_knowledge_ext.search import HybridSearchProvider

        provider = HybridSearchProvider(BM25SearchProvider(), KeywordSearchProvider())
        provider.build_index(items)

        # 'ToolConfig' appears in 1/2 docs, so BM25 score is 0.0 (as seen in repro)
        # But Keyword search should find it by substring matching.
        results = provider.search("ToolConfig", page=1, page_size=1)

        self.assertTrue(
            len(results) > 0,
            "Hybrid search should find ToolConfig via Keyword fallback",
        )
        self.assertEqual(results[0][1]["id"], "google.adk.tools.ToolConfig")


if __name__ == "__main__":
    unittest.main()
