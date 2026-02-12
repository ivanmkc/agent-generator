"""Test Api Key Manager module."""

import os
import pytest
from unittest.mock import patch

from core.api_key_manager import ApiKeyManager, KeyType


@pytest.fixture(autouse=True)
def clean_env():
    # Clear environment variables before each test to ensure isolation
    vars_to_clear = [
        "GEMINI_API_KEY",
        "GEMINI_API_KEYS_POOL",
        "CONTEXT7_API_KEY",
        "CONTEXT7_API_KEYS_POOL",
    ]
    old_vars = {v: os.environ.get(v) for v in vars_to_clear}
    for v in vars_to_clear:
        if v in os.environ:
            del os.environ[v]

    yield

    for v, val in old_vars.items():
        if val is not None:
            os.environ[v] = val
        elif v in os.environ:
            del os.environ[v]


@pytest.fixture(autouse=True)
def mock_persistence():
    with patch("core.api_key_manager.ApiKeyManager._save_stats"), patch(
        "core.api_key_manager.ApiKeyManager._load_stats"
    ):
        yield


@pytest.mark.asyncio
async def test_single_gemini_key_fallback():
    os.environ["GEMINI_API_KEY"] = "single-gemini-key"
    manager = ApiKeyManager(pool_only=False)
    assert manager.get_key_count(KeyType.GEMINI_API) == 1
    assert await manager.get_next_key(KeyType.GEMINI_API) == "single-gemini-key"
    assert await manager.get_next_key(KeyType.GEMINI_API) == "single-gemini-key"


@pytest.mark.asyncio
async def test_gemini_keys_pool():
    os.environ["GEMINI_API_KEYS_POOL"] = "key1,key2,key3"
    manager = ApiKeyManager(pool_only=False)
    assert manager.get_key_count(KeyType.GEMINI_API) == 3
    assert await manager.get_next_key(KeyType.GEMINI_API) == "key1"
    assert await manager.get_next_key(KeyType.GEMINI_API) == "key2"
    assert await manager.get_next_key(KeyType.GEMINI_API) == "key3"
    assert await manager.get_next_key(KeyType.GEMINI_API) == "key1"


@pytest.mark.asyncio
async def test_gemini_pool_takes_precedence_over_single_key():
    os.environ["GEMINI_API_KEY"] = "single-gemini-key-should-be-ignored"
    os.environ["GEMINI_API_KEYS_POOL"] = "keyA,keyB"
    manager = ApiKeyManager(pool_only=False)
    assert manager.get_key_count(KeyType.GEMINI_API) == 2
    assert await manager.get_next_key(KeyType.GEMINI_API) == "keyA"
    assert await manager.get_next_key(KeyType.GEMINI_API) == "keyB"


@pytest.mark.asyncio
async def test_no_gemini_keys():
    manager = ApiKeyManager(pool_only=False)
    assert manager.get_key_count(KeyType.GEMINI_API) == 0
    assert await manager.get_next_key(KeyType.GEMINI_API) is None


@pytest.mark.asyncio
async def test_multiple_key_types():
    os.environ["GEMINI_API_KEY"] = "gemini-single"
    os.environ["CONTEXT7_API_KEYS_POOL"] = "ctxkey1,ctxkey2"
    manager = ApiKeyManager(pool_only=False)

    assert manager.get_key_count(KeyType.GEMINI_API) == 1
    assert await manager.get_next_key(KeyType.GEMINI_API) == "gemini-single"

    assert manager.get_key_count(KeyType.CONTEXT7_API) == 2
    assert await manager.get_next_key(KeyType.CONTEXT7_API) == "ctxkey1"
    assert await manager.get_next_key(KeyType.CONTEXT7_API) == "ctxkey2"
    assert await manager.get_next_key(KeyType.CONTEXT7_API) == "ctxkey1"


@pytest.mark.asyncio
async def test_key_types_with_no_keys():
    manager = ApiKeyManager(pool_only=False)
    assert manager.get_key_count(KeyType.CONTEXT7_API) == 0
    assert await manager.get_next_key(KeyType.CONTEXT7_API) is None


@pytest.mark.asyncio
async def test_key_with_empty_string_in_pool():
    os.environ["GEMINI_API_KEYS_POOL"] = ",key1,,key2,"
    manager = ApiKeyManager(pool_only=False)
    assert manager.get_key_count(KeyType.GEMINI_API) == 2
    assert await manager.get_next_key(KeyType.GEMINI_API) == "key1"
    assert await manager.get_next_key(KeyType.GEMINI_API) == "key2"


if __name__ == "__main__":
    unittest.main()
