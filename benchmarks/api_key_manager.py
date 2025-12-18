"""
A module for managing and rotating API keys from environment variables.

This module provides a thread-safe mechanism to load multiple API keys for
different services (e.g., Gemini, Context7) from environment variables and
then rotate through them in a round-robin fashion. This helps in preventing
quota issues when making many API requests.
"""

import os
import itertools
import threading
from enum import Enum
from typing import Optional, Dict

class KeyType(Enum):
    """
    Defines the different types of API keys that can be managed.

    Each member corresponds to a specific API service and influences the
    environment variable names used to load its keys.
    """
    GEMINI_API = "GEMINI_API"
    CONTEXT7_API = "CONTEXT7_API"
    # Add other key types here as needed.
    # For example:
    # ANOTHER_SERVICE_API = "ANOTHER_SERVICE_API"

class ApiKeyManager:
    """
    Manages pools of API keys for rotation, separated by key type.

    Keys are loaded from environment variables during initialization. For each
    KeyType, the manager first looks for a pool of keys (e.g., "GEMINI_API_KEYS_POOL")
    as a comma-separated string. If no pool is found, it falls back to a single
    key variable (e.g., "GEMINI_API_KEY").

    The `get_next_key` method provides thread-safe round-robin rotation of keys
    within each pool.
    """

    def __init__(self):
        """
        Initializes the ApiKeyManager and loads all configured API key pools
        from environment variables.
        """
        self._pools: Dict[KeyType, itertools.cycle] = {}
        self._key_counts: Dict[KeyType, int] = {}
        self._lock = threading.Lock()
        self._load_all_keys()

    def _load_all_keys(self):
        """
        Internal method to iterate through all defined `KeyType`s and load
        their respective API keys into separate pools.
        """
        for key_type in KeyType:
            self._load_keys_for_type(key_type)

    def _load_keys_for_type(self, key_type: KeyType):
        """
        Loads API keys for a specific `KeyType` from environment variables.

        It prioritizes a comma-separated pool variable (e.g., "GEMINI_API_KEYS_POOL")
        over a single key variable (e.g., "GEMINI_API_KEY").

        Args:
            key_type: The `KeyType` for which to load keys.
        """
        env_var_base = key_type.value
        pool_var = f"{env_var_base}_KEYS_POOL"
        single_var = f"{env_var_base}_KEY"

        keys = []
        
        # 1. Check for a pool variable (comma-separated)
        pool_str = os.environ.get(pool_var, "")
        if pool_str:
            keys = [k.strip() for k in pool_str.split(",") if k.strip()]
        
        # 2. Fallback to standard single key if pool is empty
        if not keys:
            single_key = os.environ.get(single_var)
            if single_key:
                keys = [single_key]
        
        self._key_counts[key_type] = len(keys)
        if keys:
            self._pools[key_type] = itertools.cycle(keys)

    def get_next_key(self, key_type: KeyType = KeyType.GEMINI_API) -> Optional[str]:
        """
        Returns the next API key for the specified `key_type` in a round-robin fashion.

        This method is thread-safe, ensuring correct key rotation even under
        concurrent access.

        Args:
            key_type: The type of API key to retrieve. Defaults to `KeyType.GEMINI_API`.

        Returns:
            The next API key as a string, or `None` if no keys are configured
            for the given type.

        Example:
            To use multiple Gemini API keys:
            1. Set environment variable: `export GEMINI_API_KEYS_POOL="key1,key2,key3"`
            2. In code: `api_key = API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API)`

            To use a single Gemini API key (fallback):
            1. Set environment variable: `export GEMINI_API_KEY="my_single_gemini_key"`
            2. In code: `api_key = API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API)`
        """
        with self._lock:
            iterator = self._pools.get(key_type)
            if not iterator:
                return None
            return next(iterator)

    def get_key_count(self, key_type: KeyType) -> int:
        """
        Returns the number of API keys loaded for a specific `key_type`.

        Args:
            key_type: The type of API key.

        Returns:
            The count of keys for the given type, or 0 if no keys are loaded.
        """
        return self._key_counts.get(key_type, 0)

# Global instance of ApiKeyManager.
# This singleton can be used for convenience or as a default dependency.
API_KEY_MANAGER = ApiKeyManager()