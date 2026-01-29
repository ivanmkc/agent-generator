"""Test Search Determinism module."""

import pytest
from adk_knowledge_ext.search import BM25SearchProvider, KeywordSearchProvider

@pytest.mark.asyncio
async def test_bm25_determinism_with_shuffle():
    # Items with identical content but different IDs
    items = [
        {"id": "A", "docstring": "test content", "rank": 10},
        {"id": "B", "docstring": "test content", "rank": 5},
        {"id": "C", "docstring": "irrelevant", "rank": 1},  # Dummy for IDF
    ]

    # Provider 1: Natural order
    p1 = BM25SearchProvider()
    p1.build_index(items)
    r1 = await p1.search("test")

    # Provider 2: Reversed input order
    p2 = BM25SearchProvider()
    p2.build_index(list(reversed(items)))
    r2 = await p2.search("test")

    # Expect B first (Rank 5 < 10) regardless of input order
    assert r1[0][1]["id"] == "B"
    assert r2[0][1]["id"] == "B"

    # Exact match of results list
    assert r1 == r2

@pytest.mark.asyncio
async def test_pagination():
    # Create 20 items. Keyword search sorts by Rank ASC.
    # So Item_0 (rank 0) ... Item_19 (rank 19)
    items = [
        {"id": f"Item_{i}", "docstring": "common keyword", "rank": i}
        for i in range(20)
    ]
    provider = KeywordSearchProvider()
    provider.build_index(items)

    page1 = await provider.search("common", page=1, page_size=10)
    assert len(page1) == 10
    assert page1[0][1]["id"] == "Item_0"
    assert page1[9][1]["id"] == "Item_9"

    page2 = await provider.search("common", page=2, page_size=10)
    assert len(page2) == 10
    assert page2[0][1]["id"] == "Item_10"
    assert page2[9][1]["id"] == "Item_19"

    page3 = await provider.search("common", page=3, page_size=10)
    assert len(page3) == 0