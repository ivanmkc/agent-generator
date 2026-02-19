"""
API Key Management Module.

This module provides a robust system for managing multiple pools of API keys for different providers
(Gemini, OpenAI, Anthropic, etc.). It handles:
- Key rotation and selection strategies.
- Rate limit handling and automatic cooldowns.
- Persistence of key health statistics.
- Thread-safe and async-safe access to keys.
"""

import asyncio
import itertools
import os
import threading
import time
import json
from pathlib import Path
from enum import Enum
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from core.logging_utils import logger


class KeyType(Enum):
    """
    Defines the different types of API keys that can be managed.
    """

    GEMINI_API = "GEMINI_API"
    CONTEXT7_API = "CONTEXT7_API"
    OPENAI_API = "OPENAI_API"
    ANTHROPIC_API = "ANTHROPIC_API"
    XAI_API = "XAI_API"
    GROQ_API = "GROQ_API"
    VERTEX_API = "VERTEX_API"


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

    def __init__(
        self,
        quota_cooldown_base: float = 5.0,
        quota_cooldown_max: float = 300.0,
        generic_cooldown: float = 5.0,
        pool_only: bool = True,
    ):
        """
        Initializes the ApiKeyManager and loads all configured API key pools.

        Args:
            quota_cooldown_base: Base seconds for quota error backoff.
            quota_cooldown_max: Maximum seconds for quota error backoff.
            generic_cooldown: Seconds for generic error cooldown.
            pool_only: If True, only loads keys from *_KEYS_POOL variables.
                       Fails (returns no keys) if pool is missing, even if single key var exists.
        """
        self.quota_cooldown_base = quota_cooldown_base
        self.quota_cooldown_max = quota_cooldown_max
        self.generic_cooldown = generic_cooldown
        self.pool_only = pool_only

        self._key_stats: Dict[KeyType, Dict[str, KeyStats]] = {}
        # We keep a simple cycle iterator as a fallback/baseline for round-robin
        self._pools: Dict[KeyType, itertools.cycle] = {}
        # Mapping from run_id -> key_id for sticky sessions
        self._run_key_map: Dict[str, str] = {}
        self._lock = asyncio.Lock()  # Use asyncio.Lock for async safety

        # Persistence setup
        self._stats_file = Path(".gemini/api_key_stats.json")
        self._stats_file.parent.mkdir(parents=True, exist_ok=True)

        self._load_all_keys()
        self._load_stats()  # Load saved stats *after* keys are initialized

    async def get_key_for_run(
        self, run_id: str, key_type: KeyType = KeyType.GEMINI_API
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Gets a sticky API key for a specific run ID.
        If the run_id already has a key, returns it.
        Otherwise, rotates a new key, assigns it to the run_id, and returns it.
        """
        async with self._lock:
            # 1. Check if run_id already has a key assigned
            if run_id in self._run_key_map:
                key_id = self._run_key_map[run_id]
                stats_map = self._key_stats.get(key_type)
                if stats_map and key_id in stats_map:
                    key_stat = stats_map[key_id]
                    # Update last used even for sticky retrieval
                    key_stat.last_used = time.time()
                    self._save_stats()
                    return key_stat.key, key_id

        # Call outside the lock
        key, key_id = await self.get_next_key_with_id(key_type)

        async with self._lock:
            if key and key_id:
                self._run_key_map[run_id] = key_id
            return key, key_id

    def release_run(self, run_id: str):
        """Releases the key mapping for a run ID."""
        # This can remain sync if it doesn't await anything, but let's make it async for consistency
        # with self._lock:
        if run_id in self._run_key_map:
            del self._run_key_map[run_id]

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

        if not keys and not self.pool_only:
            single_key = os.environ.get(single_var)
            if single_key:
                keys = [single_key]

        # TODO: This shouldn't be restricted to GEMINI_API only.
        if self.pool_only and not keys and key_type == KeyType.GEMINI_API:
            raise ValueError(
                f"Environment variable '{pool_var}' is not set or empty, but pool_only=True is configured."
            )

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
                    continue  # Unknown key type in file

                if key_type in self._key_stats:
                    for k_id, k_data in keys_data.items():
                        if k_id in self._key_stats[key_type]:
                            # Update existing stats
                            current_stat = self._key_stats[key_type][k_id]
                            current_stat.status = KeyStatus(
                                k_data.get("status", "active")
                            )
                            current_stat.success_count = k_data.get("success_count", 0)
                            current_stat.failure_count = k_data.get("failure_count", 0)
                            current_stat.last_used = k_data.get("last_used", 0.0)
                            current_stat.cooldown_until = k_data.get(
                                "cooldown_until", 0.0
                            )
                            current_stat.consecutive_failures = k_data.get(
                                "consecutive_failures", 0
                            )
        except Exception as e:
            logger.error(f"[ApiKeyManager] Failed to load stats: {e}")

    def _save_stats(self):
        """Persists current stats to JSON file."""
        data = {}
        for k_type, stats_map in self._key_stats.items():
            data[k_type.value] = {}
            for k_id, stat in stats_map.items():
                # Explicitly construct dict to avoid leaking the key
                stat_dict = {
                    "id": stat.id,
                    "status": stat.status.value,
                    "success_count": stat.success_count,
                    "failure_count": stat.failure_count,
                    "last_used": stat.last_used,
                    "cooldown_until": stat.cooldown_until,
                    "consecutive_failures": stat.consecutive_failures,
                }
                data[k_type.value][k_id] = stat_dict

        try:
            # This is a quick operation, a thread lock is fine to prevent corruption
            # but we are in an async context, so we should be careful.
            # For simplicity, we assume this file write is fast enough not to block the event loop.
            # A better solution would use aiofiles.
            with open(self._stats_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"[ApiKeyManager] Failed to save stats: {e}")

    async def get_next_key_with_id(
        self, key_type: KeyType = KeyType.GEMINI_API
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Returns the best available API key. Prioritizes ACTIVE keys.
        If all are in COOLDOWN, picks the one expiring soonest.
        """
        async with self._lock:
            stats_map = self._key_stats.get(key_type)
            if not stats_map:
                return None, None

            now = time.time()
            candidates = list(stats_map.values())

            # 1. Filter out DEAD keys
            viable = [k for k in candidates if k.status != KeyStatus.DEAD]
            if not viable and candidates:
                # All dead? Reset them all to ACTIVE to try again (emergency reset)
                logger.error(
                    f"[ApiKeyManager] All keys for {key_type.value} are DEAD. Resetting all to ACTIVE."
                )
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
                logger.warning(
                    f"[ApiKeyManager] All keys on cooldown. Using key {best_key.id} (wait {wait_time:.1f}s recommended)."
                )
                best_key.last_used = now
                self._save_stats()
                return best_key.key, best_key.id

            return None, None

    async def report_result(
        self, key_type: KeyType, key_id: str, success: bool, error_message: str = None
    ):
        """
        Reports the outcome of an API call to update key stats.
        """
        async with self._lock:
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
                is_quota = error_message and (
                    "429" in error_message
                    or "Quota" in error_message
                    or "quota" in error_message
                )
                is_auth = error_message and (
                    "403" in error_message or "401" in error_message in error_message
                )

                if is_auth:
                    key_stat.status = KeyStatus.DEAD
                    logger.error(
                        f"[ApiKeyManager] Key {key_id} marked DEAD (Auth error)."
                    )
                elif is_quota:
                    # Exponential backoff: base, base*2, base*4...
                    penalty = self.quota_cooldown_base * (
                        2 ** max(0, key_stat.consecutive_failures - 1)
                    )
                    penalty = min(penalty, self.quota_cooldown_max)
                    key_stat.status = KeyStatus.COOLDOWN
                    key_stat.cooldown_until = now + penalty
                    logger.warning(
                        f"[ApiKeyManager] Key {key_id} cooldown for {penalty}s (Quota)."
                    )
                else:
                    # Generic error (timeout, 500)
                    # Short cooldown
                    key_stat.status = KeyStatus.COOLDOWN
                    key_stat.cooldown_until = now + self.generic_cooldown
                    logger.warning(
                        f"[ApiKeyManager] Key {key_id} short cooldown (Generic Error): {error_message}"
                    )

            self._save_stats()

    async def get_next_key(
        self, key_type: KeyType = KeyType.GEMINI_API
    ) -> Optional[str]:
        """
        Wrapper for backward compatibility.
        """
        key, _ = await self.get_next_key_with_id(key_type)
        return key

    def get_key_count(self, key_type: KeyType) -> int:
        return len(self._key_stats.get(key_type, {}))

    async def get_key_id(
        self, key: str, key_type: KeyType = KeyType.GEMINI_API
    ) -> Optional[str]:
        """
        Reverse lookup: Find the ID for a given key string.
        """
        async with self._lock:
            stats_map = self._key_stats.get(key_type)
            if not stats_map:
                return None

            for k_id, stat in stats_map.items():
                if stat.key == key:
                    return k_id
            return None


# Global instance of ApiKeyManager.
# This singleton can be used for convenience or as a default dependency.
API_KEY_MANAGER = ApiKeyManager()
