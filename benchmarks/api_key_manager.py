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
import time
import json
from pathlib import Path
from enum import Enum
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from colorama import init, Fore, Style

# Initialize colorama
init()

class KeyType(Enum):
    """
    Defines the different types of API keys that can be managed.
    """
    GEMINI_API = "GEMINI_API"
    CONTEXT7_API = "CONTEXT7_API"

class KeyStatus(str, Enum):
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    DEAD = "dead"

@dataclass
class KeyStats:
    key: str
    id: str
    status: KeyStatus = KeyStatus.ACTIVE
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0.0
    cooldown_until: float = 0.0
    consecutive_failures: int = 0

class ApiKeyManager:
    """
    Manages pools of API keys with smart rotation, cooldowns, and health tracking.
    Persists key health statistics to disk to optimize usage across runs.
    """

    def __init__(self):
        """
        Initializes the ApiKeyManager and loads all configured API key pools.
        """
        self._key_stats: Dict[KeyType, Dict[str, KeyStats]] = {}
        # We keep a simple cycle iterator as a fallback/baseline for round-robin
        self._pools: Dict[KeyType, itertools.cycle] = {} 
        self._lock = threading.Lock()
        
        # Persistence setup
        self._stats_file = Path(".gemini/api_key_stats.json")
        self._stats_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._load_all_keys()
        self._load_stats() # Load saved stats *after* keys are initialized

    def _load_all_keys(self):
        for key_type in KeyType:
            self._load_keys_for_type(key_type)

    def _load_keys_for_type(self, key_type: KeyType):
        env_var_base = key_type.value
        pool_var = f"{env_var_base}_KEYS_POOL"
        single_var = f"{env_var_base}_KEY"

        keys = []
        pool_str = os.environ.get(pool_var, "")
        if pool_str:
            keys = [k.strip() for k in pool_str.split(",") if k.strip()]
        
        if not keys:
            single_key = os.environ.get(single_var)
            if single_key:
                keys = [single_key]
        
        # Initialize stats for each key
        self._key_stats[key_type] = {}
        keyed_entries = []
        for i, k in enumerate(keys):
            key_id = str(i)
            # Default init, will be overwritten by _load_stats if file exists
            self._key_stats[key_type][key_id] = KeyStats(key=k, id=key_id)
            keyed_entries.append((k, key_id))
            
        if keys:
            self._pools[key_type] = itertools.cycle(keyed_entries)

    def _load_stats(self):
        """Loads stats from JSON file and updates in-memory KeyStats."""
        if not self._stats_file.exists():
            return

        try:
            with open(self._stats_file, "r") as f:
                data = json.load(f)
            
            for k_type_str, keys_data in data.items():
                try:
                    key_type = KeyType(k_type_str)
                except ValueError:
                    continue # Unknown key type in file
                
                if key_type in self._key_stats:
                    for k_id, k_data in keys_data.items():
                        if k_id in self._key_stats[key_type]:
                            # Update existing stats
                            current_stat = self._key_stats[key_type][k_id]
                            current_stat.status = KeyStatus(k_data.get("status", "active"))
                            current_stat.success_count = k_data.get("success_count", 0)
                            current_stat.failure_count = k_data.get("failure_count", 0)
                            current_stat.last_used = k_data.get("last_used", 0.0)
                            current_stat.cooldown_until = k_data.get("cooldown_until", 0.0)
                            current_stat.consecutive_failures = k_data.get("consecutive_failures", 0)
        except Exception as e:
            print(f"{Fore.RED}[ApiKeyManager] Failed to load stats: {e}{Style.RESET_ALL}")

    def _save_stats(self):
        """Persists current stats to JSON file."""
        data = {}
        for k_type, stats_map in self._key_stats.items():
            data[k_type.value] = {
                k_id: asdict(stat) for k_id, stat in stats_map.items()
            }
        
        try:
            with open(self._stats_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"{Fore.RED}[ApiKeyManager] Failed to save stats: {e}{Style.RESET_ALL}")

    def get_next_key_with_id(self, key_type: KeyType = KeyType.GEMINI_API) -> tuple[Optional[str], Optional[str]]:
        """
        Returns the best available API key. Prioritizes ACTIVE keys.
        If all are in COOLDOWN, picks the one expiring soonest.
        """
        with self._lock:
            stats_map = self._key_stats.get(key_type)
            if not stats_map:
                return None, None

            now = time.time()
            candidates = list(stats_map.values())
            
            # 1. Filter out DEAD keys
            viable = [k for k in candidates if k.status != KeyStatus.DEAD]
            if not viable and candidates:
                # All dead? Reset them all to ACTIVE to try again (emergency reset)
                print(f"{Fore.RED}[ApiKeyManager] All keys for {key_type.value} are DEAD. Resetting all to ACTIVE.{Style.RESET_ALL}")
                for k in candidates:
                    k.status = KeyStatus.ACTIVE
                    k.consecutive_failures = 0
                viable = candidates
                self._save_stats()

            if not viable:
                return None, None

            # 2. Check for ACTIVE keys
            active = [k for k in viable if k.status == KeyStatus.ACTIVE]
            
            # 3. Check for COOLDOWN keys that have expired
            # We treat them as ACTIVE immediately
            for k in viable:
                if k.status == KeyStatus.COOLDOWN and k.cooldown_until <= now:
                    k.status = KeyStatus.ACTIVE
                    k.cooldown_until = 0.0
                    active.append(k)

            # Deduplicate active list just in case
            active = list({k.id: k for k in active}.values())

            if active:
                # Pick LRU
                best_key = min(active, key=lambda k: k.last_used)
                best_key.last_used = now
                self._save_stats()
                return best_key.key, best_key.id

            # 4. If no ACTIVE keys, we are saturated.
            # Pick the COOLDOWN key that expires soonest.
            cooldowns = [k for k in viable if k.status == KeyStatus.COOLDOWN]
            if cooldowns:
                best_key = min(cooldowns, key=lambda k: k.cooldown_until)
                wait_time = max(0, best_key.cooldown_until - now)
                print(f"{Fore.YELLOW}[ApiKeyManager] All keys on cooldown. Using key {best_key.id} (wait {wait_time:.1f}s recommended).{Style.RESET_ALL}")
                best_key.last_used = now
                self._save_stats()
                return best_key.key, best_key.id
            
            return None, None

    def report_result(self, key_type: KeyType, key_id: str, success: bool, error_message: str = None):
        """
        Reports the outcome of an API call to update key stats.
        """
        with self._lock:
            stats_map = self._key_stats.get(key_type)
            if not stats_map or key_id not in stats_map:
                return

            key_stat = stats_map[key_id]
            now = time.time()

            if success:
                key_stat.success_count += 1
                key_stat.consecutive_failures = 0
                if key_stat.status == KeyStatus.COOLDOWN:
                    key_stat.status = KeyStatus.ACTIVE
                    key_stat.cooldown_until = 0.0
            else:
                key_stat.failure_count += 1
                key_stat.consecutive_failures += 1
                
                # Analyze error to determine penalty
                is_quota = error_message and ("429" in error_message or "Quota" in error_message or "quota" in error_message)
                is_auth = error_message and ("403" in error_message or "401" in error_message in error_message)
                
                if is_auth:
                    key_stat.status = KeyStatus.DEAD
                    print(f"{Fore.RED}[ApiKeyManager] Key {key_id} marked DEAD (Auth error).{Style.RESET_ALL}")
                elif is_quota:
                    # Exponential backoff: 5s, 10s, 20s...
                    # Default to 5s for first quota hit
                    penalty = 5 * (2 ** max(0, key_stat.consecutive_failures - 1))
                    penalty = min(penalty, 300) # Max 5 minutes
                    key_stat.status = KeyStatus.COOLDOWN
                    key_stat.cooldown_until = now + penalty
                    print(f"{Fore.YELLOW}[ApiKeyManager] Key {key_id} cooldown for {penalty}s (Quota).{Style.RESET_ALL}")
                else:
                    # Generic error (timeout, 500)
                    # Short cooldown
                    key_stat.status = KeyStatus.COOLDOWN
                    key_stat.cooldown_until = now + 5 # 5s pause
                    print(f"{Fore.YELLOW}[ApiKeyManager] Key {key_id} short cooldown (Generic Error).{Style.RESET_ALL}")
            
            self._save_stats()

    def get_next_key(self, key_type: KeyType = KeyType.GEMINI_API) -> Optional[str]:
        """
        Wrapper for backward compatibility.
        """
        key, _ = self.get_next_key_with_id(key_type)
        return key

    def get_key_count(self, key_type: KeyType) -> int:
        return len(self._key_stats.get(key_type, {}))

# Global instance of ApiKeyManager.
# This singleton can be used for convenience or as a default dependency.
API_KEY_MANAGER = ApiKeyManager()