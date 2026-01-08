import os
import unittest
import threading
from unittest.mock import patch

from benchmarks.api_key_manager import ApiKeyManager, KeyType


class TestApiKeyManager(unittest.TestCase):

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

    def test_single_gemini_key_fallback(self):
        os.environ["GEMINI_API_KEY"] = "single-gemini-key"
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 1)
        self.assertEqual(manager.get_next_key(KeyType.GEMINI_API), "single-gemini-key")
        self.assertEqual(
            manager.get_next_key(KeyType.GEMINI_API), "single-gemini-key"
        )  # Should cycle same key

    def test_gemini_keys_pool(self):
        os.environ["GEMINI_API_KEYS_POOL"] = "key1,key2,key3"
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 3)
        self.assertEqual(manager.get_next_key(KeyType.GEMINI_API), "key1")
        self.assertEqual(manager.get_next_key(KeyType.GEMINI_API), "key2")
        self.assertEqual(manager.get_next_key(KeyType.GEMINI_API), "key3")
        self.assertEqual(manager.get_next_key(KeyType.GEMINI_API), "key1")  # Cycle back

    def test_gemini_pool_takes_precedence_over_single_key(self):
        os.environ["GEMINI_API_KEY"] = "single-gemini-key-should-be-ignored"
        os.environ["GEMINI_API_KEYS_POOL"] = "keyA,keyB"
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 2)
        self.assertEqual(manager.get_next_key(KeyType.GEMINI_API), "keyA")
        self.assertEqual(manager.get_next_key(KeyType.GEMINI_API), "keyB")

    def test_no_gemini_keys(self):
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 0)
        self.assertIsNone(manager.get_next_key(KeyType.GEMINI_API))

    def test_multiple_key_types(self):
        os.environ["GEMINI_API_KEY"] = "gemini-single"
        os.environ["CONTEXT7_API_KEYS_POOL"] = "ctxkey1,ctxkey2"
        manager = ApiKeyManager()

        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 1)
        self.assertEqual(manager.get_next_key(KeyType.GEMINI_API), "gemini-single")

        self.assertEqual(manager.get_key_count(KeyType.CONTEXT7_API), 2)
        self.assertEqual(manager.get_next_key(KeyType.CONTEXT7_API), "ctxkey1")
        self.assertEqual(manager.get_next_key(KeyType.CONTEXT7_API), "ctxkey2")
        self.assertEqual(manager.get_next_key(KeyType.CONTEXT7_API), "ctxkey1")

    def test_thread_safety(self):
        os.environ["GEMINI_API_KEYS_POOL"] = "tkey1,tkey2,tkey3"
        manager = ApiKeyManager()

        results = []

        def worker():
            results.append(manager.get_next_key(KeyType.GEMINI_API))

        threads = []
        for _ in range(100):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify that all keys were rotated through in a round-robin fashion
        # The exact order might vary due to thread scheduling, but the distribution should be even
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

    def test_multiple_pools_thread_safety(self):
        """
        Verifies that multiple key pools can be accessed concurrently without
        interference and that rotation remains correct for each pool.
        """
        os.environ["GEMINI_API_KEYS_POOL"] = "g1,g2,g3"
        os.environ["CONTEXT7_API_KEYS_POOL"] = "c1,c2"
        manager = ApiKeyManager()

        gemini_results = []
        context7_results = []

        # Lock to protect results lists during concurrent append
        results_lock = threading.Lock()

        def worker(key_type, results_list):
            key = manager.get_next_key(key_type)
            with results_lock:
                results_list.append(key)

        threads = []
        # Launch 50 threads for Gemini pool
        for _ in range(50):
            t = threading.Thread(
                target=worker, args=(KeyType.GEMINI_API, gemini_results)
            )
            threads.append(t)
            t.start()

        # Launch 50 threads for Context7 pool
        for _ in range(50):
            t = threading.Thread(
                target=worker, args=(KeyType.CONTEXT7_API, context7_results)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

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

    def test_key_types_with_no_keys(self):
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.CONTEXT7_API), 0)
        self.assertIsNone(manager.get_next_key(KeyType.CONTEXT7_API))

    def test_key_with_empty_string_in_pool(self):
        os.environ["GEMINI_API_KEYS_POOL"] = ",key1,,key2,"
        manager = ApiKeyManager()
        self.assertEqual(manager.get_key_count(KeyType.GEMINI_API), 2)
        self.assertEqual(manager.get_next_key(KeyType.GEMINI_API), "key1")
        self.assertEqual(manager.get_next_key(KeyType.GEMINI_API), "key2")


if __name__ == "__main__":
    unittest.main()
