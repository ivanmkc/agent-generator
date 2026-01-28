import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from vibeshare.src.analyze_vibeshare import run_analysis
from vibeshare.src.models.model import Model

# Define a mock model class
class MockModel(Model):
    def __init__(self, model_name="mock-model"):
        self.model_name = model_name

    async def predict(self, prompt, **kwargs):
        return f"Mock response to: {prompt}"

@pytest.fixture
def mock_models():
    return [MockModel("mock-gpt-4"), MockModel("mock-claude-3")]

@pytest.fixture
def mock_prompts():
    return [{"category": "test-cat", "prompt": "test prompt 1"}]

@pytest.mark.asyncio
async def test_run_analysis_end_to_end_mock(tmp_path, mock_models, mock_prompts):
    """
    Test the full analyze_vibeshare pipeline with mocked components.
    This ensures the orchestration logic works without hitting real APIs.
    """
    
    # 1. Setup paths
    results_file = tmp_path / "vibeshare_results.json"
    
    # Simple in-memory cache behavior
    cache_store = {}
    
    def mock_cache_get(model_name, prompt):
        # We need to replicate the key generation logic roughly or just use the args
        # The real cache uses a hash, but here we can just use a tuple key
        return cache_store.get((model_name, prompt))
        
    def mock_cache_set(model_name, prompt, data):
        cache_store[(model_name, prompt)] = data

    # 2. Mock dependencies
    with patch("vibeshare.src.analyze_vibeshare.run_verification", new_callable=AsyncMock) as mock_verify, \
         patch("vibeshare.src.analyze_vibeshare.load_prompts", return_value=mock_prompts), \
         patch("vibeshare.src.analyze_vibeshare.VIBESHARE_RESULTS_FILE", results_file), \
         patch("vibeshare.src.inference.CACHE_MANAGER") as mock_cache:
         
        # Configure mock verification to return our mock models
        mock_verify.return_value = mock_models
        
        # Configure cache side effects
        mock_cache.get.side_effect = mock_cache_get
        mock_cache.set.side_effect = mock_cache_set
        
        # 3. Run the analysis
        await run_analysis()
        
        # 4. Verify results
        assert results_file.exists()
        
        with open(results_file, "r") as f:
            data = json.load(f)
            
        assert len(data) == len(mock_models) * len(mock_prompts)
        
        # Check first result
        # We don't know the order guarantees, so search
        found = False
        for res in data:
            if res["model_name"] == "mock-gpt-4" and res["prompt"] == "test prompt 1":
                assert res["response"] == "Mock response to: test prompt 1"
                assert res["success"] is True
                found = True
        assert found

        # Verify interactions
        mock_verify.assert_called_once()