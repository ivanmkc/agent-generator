import pytest
import json
from unittest.mock import MagicMock
import pandas as pd

# Mock streamlit to prevent it from running during tests
# This needs to be done before importing benchmark_viewer
import sys

sys.modules["streamlit"] = MagicMock()

from tools.benchmark_viewer import _get_concise_error_message


def test_get_concise_error_message_with_gemini_client_error_json():
    """Tests that a concise message is extracted from GEMINI_CLIENT_ERROR JSON content."""
    mock_row = {
        "trace_logs": [
            {"type": "tool_use", "tool_name": "some_tool"},
            {
                "type": "GEMINI_CLIENT_ERROR",
                "content": json.dumps({"error": {"message": "Quota exceeded."}}),
            },
            {"type": "model_response", "content": "Hello"},
        ]
    }
    expected_message = "❌ Error: Quota exceeded."
    assert (
        _get_concise_error_message(mock_row, mock_row["trace_logs"]) == expected_message
    )


def test_get_concise_error_message_with_gemini_client_error_dict():
    """Tests that a concise message is extracted when GEMINI_CLIENT_ERROR content is a dict."""
    mock_row = {
        "trace_logs": [
            {"type": "tool_use", "tool_name": "some_tool"},
            {
                "type": "GEMINI_CLIENT_ERROR",
                "content": {"error": {"message": "Quota exceeded (dict)."}},
            },
            {"type": "model_response", "content": "Hello"},
        ]
    }
    expected_message = "❌ Error: Quota exceeded (dict)."
    assert (
        _get_concise_error_message(mock_row, mock_row["trace_logs"]) == expected_message
    )


def test_get_concise_error_message_with_gemini_client_error_non_json():
    """Tests that a generic message is returned if GEMINI_CLIENT_ERROR content is not JSON."""
    mock_row = {
        "trace_logs": [
            {"type": "tool_use", "tool_name": "some_tool"},
            {"type": "GEMINI_CLIENT_ERROR", "content": "Some arbitrary error text."},
            {"type": "model_response", "content": "Hello"},
        ]
    }
    expected_message = "Validation Failed (See 'Validation Error' tab for details)"
    assert (
        _get_concise_error_message(mock_row, mock_row["trace_logs"]) == expected_message
    )


def test_get_concise_error_message_without_gemini_client_error():
    """Tests that a generic message is returned if no GEMINI_CLIENT_ERROR is found."""
    mock_row = {
        "trace_logs": [
            {"type": "tool_use", "tool_name": "some_tool"},
            {"type": "model_response", "content": "Hello"},
        ]
    }
    expected_message = "Validation Failed (See 'Validation Error' tab for details)"
    assert (
        _get_concise_error_message(mock_row, mock_row["trace_logs"]) == expected_message
    )


def test_get_concise_error_message_with_empty_trace_logs():
    """Tests that a generic message is returned for empty trace logs."""
    mock_row = {"trace_logs": []}
    expected_message = "Validation Failed (See 'Validation Error' tab for details)"
    assert _get_concise_error_message(mock_row, []) == expected_message


def test_get_concise_error_message_with_no_trace_logs_key():
    """Tests that a generic message is returned if 'trace_logs' key is missing."""
    mock_row = {"some_other_key": "value"}
    expected_message = "Validation Failed (See 'Validation Error' tab for details)"
    assert _get_concise_error_message(mock_row, []) == expected_message
