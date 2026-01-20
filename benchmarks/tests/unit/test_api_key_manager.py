import os
import unittest
import asyncio
from unittest.mock import patch

from benchmarks.api_key_manager import ApiKeyManager, KeyType


class TestApiKeyManager(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Clear environment variables before each test to ensure isolation
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        if "GEMINI_API_KEYS_POOL" in os.environ:
            del os.environ["GEMINI_API_KEYS_POOL"]
        if "CONTEXT7_API_KEY" in os.environ:
            del os.environ["CONTEXT7_API_KEY"]
        if "CONTEXT7_API_KEYS_POOL" in os.environ:
            del os.environ["CONTEXT7_API_KEYS_POOL"]
        
        # Patch the stats file path to avoid persistence between tests
        self.stats_patcher = patch("benchmarks.api_key_manager.ApiKeyManager._save_stats", autospec=True)
        self.mock_save_stats = self.stats_patcher.start()
        
        # Also patch load_stats to do nothing
        self.load_stats_patcher = patch("benchmarks.api_key_manager.ApiKeyManager._load_stats", autospec=True)
        self.mock_load_stats = self.load_stats_patcher.start()

    def tearDown(self):
        self.stats_patcher.stop()
        self.load_stats_patcher.stop()

    async def test_single_gemini_key_fallback(self):
        os.environ["GEMINI_API_KEY"] = "single-gemini-key"
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 1)
        self.assertEqual(await manager.get_next_key(KeyType.GEMINI_API), "single-gemini-key")
        self.assertEqual(
            await manager.get_next_key(KeyType.GEMINI_API), "single-gemini-key"
        )  # Should cycle same key

    async def test_gemini_keys_pool(self):
        os.environ["GEMINI_API_KEYS_POOL"] = "key1,key2,key3"
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 3)
        self.assertEqual(await manager.get_next_key(KeyType.GEMINI_API), "key1")
        self.assertEqual(await manager.get_next_key(KeyType.GEMINI_API), "key2")
        self.assertEqual(await manager.get_next_key(KeyType.GEMINI_API), "key3")
        self.assertEqual(await manager.get_next_key(KeyType.GEMINI_API), "key1")  # Cycle back

    async def test_gemini_pool_takes_precedence_over_single_key(self):
        os.environ["GEMINI_API_KEY"] = "single-gemini-key-should-be-ignored"
        os.environ["GEMINI_API_KEYS_POOL"] = "keyA,keyB"
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 2)
        self.assertEqual(await manager.get_next_key(KeyType.GEMINI_API), "keyA")
        self.assertEqual(await manager.get_next_key(KeyType.GEMINI_API), "keyB")

    async def test_no_gemini_keys(self):
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 0)
        self.assertIsNone(await manager.get_next_key(KeyType.GEMINI_API))

    async def test_multiple_key_types(self):
        os.environ["GEMINI_API_KEY"] = "gemini-single"
        os.environ["CONTEXT7_API_KEYS_POOL"] = "ctxkey1,ctxkey2"
        manager = ApiKeyManager()

        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 1)
        self.assertEqual(await manager.get_next_key(KeyType.GEMINI_API), "gemini-single")

        self.assertEqual(manager.get_key_count(KeyType.CONTEXT7_API), 2)
        self.assertEqual(await manager.get_next_key(KeyType.CONTEXT7_API), "ctxkey1")
        self.assertEqual(await manager.get_next_key(KeyType.CONTEXT7_API), "ctxkey2")
        self.assertEqual(await manager.get_next_key(KeyType.CONTEXT7_API), "ctxkey1")

    async def test_async_concurrency(self):
        os.environ["GEMINI_API_KEYS_POOL"] = "tkey1,tkey2,tkey3"
        manager = ApiKeyManager()

        tasks = [manager.get_next_key(KeyType.GEMINI_API) for _ in range(100)]
        results = await asyncio.gather(*tasks)

        # Verify that all keys were rotated through in a round-robin fashion
        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 3)
        self.assertEqual(len(results), 100)

        # Count occurrences of each key
        key_counts = {"tkey1": 0, "tkey2": 0, "tkey3": 0}
        for key in results:
            key_counts[key] += 1

        # With 100 calls and 3 keys, each key should be called ~33-34 times
        for key, count in key_counts.items():
            self.assertTrue(
                33 <= count <= 34, f"Key {key} count {count} is not as expected"
            )

    async def test_multiple_pools_async_concurrency(self):
        """
        Verifies that multiple key pools can be accessed concurrently without
        interference.
        """
        os.environ["GEMINI_API_KEYS_POOL"] = "g1,g2,g3"
        os.environ["CONTEXT7_API_KEYS_POOL"] = "c1,c2"
        manager = ApiKeyManager()

        gemini_tasks = [manager.get_next_key(KeyType.GEMINI_API) for _ in range(50)]
        context7_tasks = [manager.get_next_key(KeyType.CONTEXT7_API) for _ in range(50)]

        gemini_results = await asyncio.gather(*gemini_tasks)
        context7_results = await asyncio.gather(*context7_tasks)

        # Verify Gemini results (3 keys, 50 requests -> ~16-17 each)
        self.assertEqual(len(gemini_results), 50)
        g_counts = {k: gemini_results.count(k) for k in ["g1", "g2", "g3"]}
        for k, count in g_counts.items():
            self.assertTrue(
                16 <= count <= 17, f"Gemini key {k} count {count} unexpected"
            )

        # Verify Context7 results (2 keys, 50 requests -> 25 each)
        self.assertEqual(len(context7_results), 50)
        c_counts = {k: context7_results.count(k) for k in ["c1", "c2"]}
        for k, count in c_counts.items():
            self.assertEqual(count, 25, f"Context7 key {k} count {count} unexpected")

    async def test_key_types_with_no_keys_async(self):
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.CONTEXT7_API), 0)
        self.assertIsNone(await manager.get_next_key(KeyType.CONTEXT7_API))

    async def test_key_with_empty_string_in_pool(self):
        os.environ["GEMINI_API_KEYS_POOL"] = ",key1,,key2,"
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 2)
        self.assertEqual(await manager.get_next_key(KeyType.GEMINI_API), "key1")
        self.assertEqual(await manager.get_next_key(KeyType.GEMINI_API), "key2")


if __name__ == "__main__":
    unittest.main()