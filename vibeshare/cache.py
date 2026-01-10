import json
import os
import hashlib
from typing import Optional, Dict, Any

CACHE_FILE = "vibeshare_cache.json"

class CacheManager:
    def __init__(self, cache_file: str = CACHE_FILE):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Corrupt cache file {self.cache_file}. Starting fresh.")
                return {}
        return {}

    def _get_key(self, model_name: str, prompt: str) -> str:
        """Creates a unique key for the model and prompt combination."""
        # Using hash of prompt to keep keys short and avoid filesystem issues if we switched to file-per-entry
        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
        return f"{model_name}::{prompt_hash}"

    def get(self, model_name: str, prompt: str) -> Optional[Dict[str, Any]]:
        key = self._get_key(model_name, prompt)
        return self.cache.get(key)

    def set(self, model_name: str, prompt: str, data: Dict[str, Any]):
        key = self._get_key(model_name, prompt)
        self.cache[key] = data
        self._save_cache()

    def _save_cache(self):
        # In a high-concurrency setup, this simple write might have race conditions.
        # But for this script, we can rely on eventual consistency or simple file locking if needed.
        # For now, let's keep it simple. If multiple tasks write, we might overwrite.
        # Ideally, we should load-modify-save or append.
        # Better yet, since we are using asyncio, we can assume this runs in the main process
        # provided we don't use multiprocessing.
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)

CACHE_MANAGER = CacheManager()
