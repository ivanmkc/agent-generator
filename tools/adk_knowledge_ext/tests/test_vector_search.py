import pytest
import numpy as np
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from adk_knowledge_ext.search import VectorSearchProvider

@pytest.fixture
def mock_index_dir(tmp_path):
    vectors = np.array([[1.0, 0.0], [0.0, 1.0]])
    metadata = [
        {"id": "class.A", "type": "CLASS", "rank": 1},
        {"id": "class.B", "type": "CLASS", "rank": 2}
    ]
    np.save(tmp_path / "targets_vectors.npy", vectors)
    with open(tmp_path / "targets_meta.json", "w") as f:
        json.dump(metadata, f)
    return tmp_path

@pytest.fixture
def items():
    return [
        {"id": "class.A", "docstring": "Apple"},
        {"id": "class.B", "docstring": "Banana"}
    ]

@pytest.mark.asyncio
async def test_vector_search_success(mock_index_dir, items):
    provider = VectorSearchProvider(mock_index_dir, api_key="fake_key")
    provider.build_index(items)
    
    # Mock GenAI client
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Mock embedding for [1.0, 0.1] -> should favor class.A
    mock_response.embeddings = [MagicMock(values=[1.0, 0.1])]
    mock_client.models.embed_content.return_value = mock_response
    
    with patch.object(provider, "_get_client", return_value=mock_client):
        results = await provider.search("fruit")
        
        assert len(results) > 0
        score, item = results[0]
        assert item["id"] == "class.A"
        assert score > 0.9

@pytest.mark.asyncio
async def test_vector_search_no_index(tmp_path):
    provider = VectorSearchProvider(tmp_path, api_key="fake_key")
    provider.build_index([])
    results = await provider.search("query")
    assert results == []
