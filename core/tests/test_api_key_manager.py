import json
import os
from pathlib import Path
from unittest.mock import patch
import pytest
from core.api_key_manager import ApiKeyManager, KeyType

class TestApiKeyManager:
    def test_save_stats_excludes_key(self, tmp_path):
        """
        Verify that _save_stats does not write the 'key' field to the JSON file.
        """
        stats_file = tmp_path / "test_stats.json"
        
        # We patch Path just for the __init__ to not fail or write to real .gemini
        # But wait, __init__ creates the parent dir of .gemini/api_key_stats.json.
        # We should probably mock the Path used in __init__ or just let it happen (it's in the project root).
        # Better to patch `core.api_key_manager.Path` to point to our temp file? 
        # But Path is imported.
        
        # Simpler: just set the env var and let it init (it might try to mkdir .gemini, which is fine as it likely exists).
        # Then swap the _stats_file before calling _save_stats.
        
        with patch.dict(os.environ, {"GEMINI_API_KEYS_POOL": "secret_key_1,secret_key_2"}):
            # We suppress the mkdir call to avoid touching real fs if possible, 
            # but it's harmless if it exists.
            # actually, if we want to be clean, we can patch mkdir.
            with patch("pathlib.Path.mkdir"):
                manager = ApiKeyManager(pool_only=True)
            
            # Redirect persistence to tmp_path
            manager._stats_file = stats_file
            
            # Save stats
            manager._save_stats()
            
            assert stats_file.exists()
            with open(stats_file) as f:
                data = json.load(f)
            
            # Check GEMINI_API stats
            gemini_stats = data.get(KeyType.GEMINI_API.value, {})
            assert len(gemini_stats) == 2
            
            for k_id, stat in gemini_stats.items():
                # CRITICAL CHECK: "key" should NOT be present
                assert "key" not in stat, f"Key was leaked in stat for {k_id}"
                
                # Check other fields are preserved
                assert "id" in stat
                assert stat["id"] == k_id
                assert "status" in stat

    def test_load_stats_preserves_keys(self, tmp_path):
        """
        Verify that loading stats updates the stats but keeps the keys loaded from env.
        """
        stats_file = tmp_path / "test_stats_load.json"
        
        # Create a dummy stats file WITHOUT keys (as it should be)
        stats_data = {
            KeyType.GEMINI_API.value: {
                "0": {"id": "0", "status": "dead", "failure_count": 5},
                "1": {"id": "1", "status": "active", "success_count": 10}
            }
        }
        with open(stats_file, "w") as f:
            json.dump(stats_data, f)
            
        with patch.dict(os.environ, {"GEMINI_API_KEYS_POOL": "secret_key_1,secret_key_2"}):
            with patch("pathlib.Path.mkdir"):
                manager = ApiKeyManager(pool_only=True)
            
            # Point to our prepared stats file
            manager._stats_file = stats_file
            
            # Trigger load
            manager._load_stats()
            
            # Check in-memory stats
            gemini_stats = manager._key_stats[KeyType.GEMINI_API]
            
            # Key "0"
            assert gemini_stats["0"].key == "secret_key_1" # Key from env preserved
            assert gemini_stats["0"].status == "dead"      # Status from file loaded
            assert gemini_stats["0"].failure_count == 5
            
            # Key "1"
            assert gemini_stats["1"].key == "secret_key_2"
            assert gemini_stats["1"].status == "active"
            assert gemini_stats["1"].success_count == 10
