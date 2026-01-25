import unittest
from adk_knowledge_ext.search import BM25SearchProvider, KeywordSearchProvider

class TestSearchDeterminism(unittest.TestCase):
    def test_bm25_determinism_with_shuffle(self):
        # Items with identical content but different IDs
        items = [
            {"id": "A", "docstring": "test content", "rank": 10},
            {"id": "B", "docstring": "test content", "rank": 5}, 
            {"id": "C", "docstring": "irrelevant", "rank": 1}, # Dummy for IDF
        ]
        
        # Provider 1: Natural order
        p1 = BM25SearchProvider()
        p1.build_index(items)
        r1 = p1.search("test")
        
        # Provider 2: Reversed input order
        p2 = BM25SearchProvider()
        p2.build_index(list(reversed(items)))
        r2 = p2.search("test")
        
        # Expect B first (Rank 5 < 10) regardless of input order
        self.assertEqual(r1[0][1]["id"], "B")
        self.assertEqual(r2[0][1]["id"], "B")
        
        # Exact match of results list
        self.assertEqual(r1, r2)
        
    def test_pagination(self):
        # Create 20 items. Keyword search sorts by Rank ASC.
        # So Item_0 (rank 0) ... Item_19 (rank 19)
        items = [{"id": f"Item_{i}", "docstring": "common keyword", "rank": i} for i in range(20)]
        provider = KeywordSearchProvider()
        provider.build_index(items)
        
        page1 = provider.search("common", page=1, page_size=10)
        self.assertEqual(len(page1), 10)
        self.assertEqual(page1[0][1]["id"], "Item_0")
        self.assertEqual(page1[9][1]["id"], "Item_9")
        
        page2 = provider.search("common", page=2, page_size=10)
        self.assertEqual(len(page2), 10)
        self.assertEqual(page2[0][1]["id"], "Item_10")
        self.assertEqual(page2[9][1]["id"], "Item_19")
        
        page3 = provider.search("common", page=3, page_size=10)
        self.assertEqual(len(page3), 0)

if __name__ == '__main__':
    unittest.main()
