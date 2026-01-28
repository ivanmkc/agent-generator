import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock, mock_open
from tools.analysis.summarize_cases import CaseDocManager, CaseDocCache, CaseDocEntry

@pytest.fixture
def mock_case_manager():
    return CaseDocManager(doc_path="dummy_path.yaml")

@pytest.mark.asyncio
async def test_get_one_liner_cached(mock_case_manager):
    """Test retrieving a one-liner from the cache (hit)."""
    
    # Mock the cache loading
    mock_data = CaseDocCache(
        cases={
            "case_1": CaseDocEntry(one_liner="Cached summary", checksum="5d41402abc4b2a76b9719d911017c592")
        }
    )
    
    # "hello" md5 is 5d41402abc4b2a76b9719d911017c592
    
    with patch.object(mock_case_manager, '_load_cache', return_value=mock_data):
        summary = await mock_case_manager.get_one_liner("case_1", "hello", "model")
        assert summary == "Cached summary"

@pytest.mark.asyncio
async def test_get_one_liner_miss_generates(mock_case_manager):
    """Test that a cache miss triggers generation."""
    
    # Mock empty cache
    with patch.object(mock_case_manager, '_load_cache', return_value=CaseDocCache()):
        # Mock the generation function
        with patch.object(mock_case_manager, '_generate_summary', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "Generated summary"
            
            # Mock the file update (don't actually write)
            with patch.object(mock_case_manager, '_update_cache') as mock_update:
                
                summary = await mock_case_manager.get_one_liner("case_new", "prompt", "model")
                
                assert summary == "Generated summary"
                mock_gen.assert_called_once()
                mock_update.assert_called_once()

@pytest.mark.asyncio
async def test_checksum_mismatch_regenerates(mock_case_manager):
    """Test that if the prompt changes, we regenerate."""
    
    old_checksum = "old_hash"
    mock_data = CaseDocCache(
        cases={
            "case_1": CaseDocEntry(one_liner="Old summary", checksum=old_checksum)
        }
    )
    
    with patch.object(mock_case_manager, '_load_cache', return_value=mock_data):
        with patch.object(mock_case_manager, '_generate_summary', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "New summary"
            with patch.object(mock_case_manager, '_update_cache') as mock_update:
                
                # "hello" has a specific hash, definitely not "old_hash"
                summary = await mock_case_manager.get_one_liner("case_1", "hello", "model")
                
                assert summary == "New summary"
                mock_gen.assert_called_once()
