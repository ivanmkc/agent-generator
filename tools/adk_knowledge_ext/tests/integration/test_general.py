"""Test Integration module."""

import os
import sys
import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add package source to path for testing
PROJECT_ROOT = Path(__file__).resolve().parents[4]
EXT_SRC = PROJECT_ROOT / "tools" / "adk_knowledge_ext" / "src"
sys.path.insert(0, str(EXT_SRC))

# Just import normally
from adk_knowledge_ext import server, index

def test_nested_symbol_lookup():
    """Reproduces the bug where nested symbols fail."""
    # Reset singleton
    index._global_index = index.KnowledgeIndex()

    mock_items = [
        {
            "fqn": "google.adk.models.base_llm_connection.BaseLlmConnection",
            "type": "class",
            "file_path": "google/adk/models/base_llm_connection.py",
            "docstring": "Base class for LLM connections.",
        }
    ]

    # Mock loading logic
    index.get_index()._items = mock_items
    index.get_index()._fqn_map = {item["fqn"]: item for item in mock_items}

    method_fqn = "google.adk.models.base_llm_connection.BaseLlmConnection.send_history"

    # 1. Test Inspect
    # We must patch _ensure_index because it validates env vars which are missing here
    with patch.object(server, "_ensure_index", return_value=None):
        result_inspect = server.inspect_symbol(fqn=method_fqn)
        assert f"Symbol '{method_fqn}' not found in index" not in result_inspect
        assert "BaseLlmConnection" in result_inspect

    # 2. Test Read Source (Mocked)
    expected_source = "class BaseLlmConnection:\n    def send_history(self, history): return True"

    # Mock _get_reader to return a mock reader that returns our expected source
    mock_reader = MagicMock()
    mock_reader.read_source.return_value = expected_source

    with patch.object(server, "_get_reader", return_value=mock_reader), \
         patch.object(server, "_ensure_index", return_value=None):

        result_read = server.read_source_code(fqn=method_fqn)

        assert "def send_history(self, history):" in result_read
        assert "class BaseLlmConnection" in result_read


def test_real_index_integrity():
    """Verifies that the extension works with the actual ranked_targets.yaml in this repo."""
    from core.config import RANKED_TARGETS_FILE
    REAL_INDEX_PATH = RANKED_TARGETS_FILE

    if not REAL_INDEX_PATH.exists():
        pytest.skip(f"Real index not found at {REAL_INDEX_PATH}")

    # Configure environment to make _ensure_index happy and load the correct file
    os.environ["TARGET_REPO_URL"] = "https://github.com/google/adk-python.git"
    os.environ["TARGET_VERSION"] = "v1.20.0" # Dummy
    os.environ["EMBEDDINGS_FOLDER_PATH"] = str(REAL_INDEX_PATH)
    
    # Reset singleton just in case
    index._global_index = index.KnowledgeIndex()

    # Manually trigger load to get items for iteration
    index.get_index().load(REAL_INDEX_PATH)

    items = index.get_index()._items
    assert len(items) > 0

    # Ensure calls use keywords
    with patch.object(server, "_ensure_index", return_value=None):
        for item in items[:10]:
            fqn = item.get("id") or item.get("fqn")
            if not fqn:
                continue

            # Inspect should always work if loaded
            res = server.inspect_symbol(fqn=fqn)
            assert (
                f"Symbol '{fqn}' not found in index" not in res
            ), f"Inspect failed for {fqn}"
