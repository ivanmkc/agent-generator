import pytest
import json
from unittest.mock import MagicMock
import pandas as pd

# Mock streamlit to prevent it from running during tests
# This needs to be done before importing benchmark_viewer
import sys

sys.modules["streamlit"] = MagicMock()

from tools.benchmark_viewer import _get_concise_error_message, merge_consecutive_events, get_run_status
from benchmarks.data_models import TraceLogEvent, TraceEventType


def test_get_run_status_completed(tmp_path, monkeypatch):
    """Tests that a run with results.json is marked Completed."""
    run_id = "test_run"
    (tmp_path / run_id).mkdir()
    (tmp_path / run_id / "results.json").write_text("[]")
    
    # Mock artifact_manager.get_file to use tmp_path
    from tools import benchmark_viewer
    monkeypatch.setattr(benchmark_viewer.artifact_manager, "get_file", lambda rid, fname: tmp_path / rid / fname if (tmp_path / rid / fname).exists() else None)
    
    assert get_run_status(run_id) == "Completed"


def test_get_run_status_pending(tmp_path, monkeypatch):
    """Tests that a run with trace.yaml but no results.json is marked Pending."""
    run_id = "test_run_pending"
    (tmp_path / run_id).mkdir()
    (tmp_path / run_id / "trace.yaml").write_text("---")
    
    from tools import benchmark_viewer
    monkeypatch.setattr(benchmark_viewer.artifact_manager, "get_file", lambda rid, fname: tmp_path / rid / fname if (tmp_path / rid / fname).exists() else None)
    
    assert get_run_status(run_id) == "Pending/Failed"


def test_merge_consecutive_events_empty():
    """Tests that an empty list returns an empty list."""
    assert merge_consecutive_events([]) == []


def test_merge_consecutive_events_single():
    """Tests that a single event is returned as is."""
    events = [{"type": "message", "role": "user", "content": "Hello"}]
    assert merge_consecutive_events(events) == events


def test_merge_consecutive_events_merge_messages_same_role():
    """Tests that consecutive messages from the same role are merged."""
    events = [
        {"type": "message", "role": "user", "content": "Hello"},
        {"type": "message", "role": "user", "content": "World"},
    ]
    expected = [{"type": "message", "role": "user", "content": "Hello\nWorld"}]
    assert merge_consecutive_events(events) == expected


def test_merge_consecutive_events_no_merge_diff_role():
    """Tests that consecutive messages from different roles are NOT merged."""
    events = [
        {"type": "message", "role": "user", "content": "Hello"},
        {"type": "message", "role": "ai", "content": "Hi there"},
    ]
    assert merge_consecutive_events(events) == events


def test_merge_consecutive_events_merge_cli_output():
    """Tests that consecutive CLI outputs of the same type are merged."""
    events = [
        {"type": "CLI_STDOUT_FULL", "content": "Line 1\n"},
        {"type": "CLI_STDOUT_FULL", "content": "Line 2"},
    ]
    expected = [{"type": "CLI_STDOUT_FULL", "content": "Line 1\nLine 2"}]
    assert merge_consecutive_events(events) == expected


def test_merge_consecutive_events_no_merge_diff_cli_type():
    """Tests that CLI stdout and stderr are NOT merged."""
    events = [
        {"type": "CLI_STDOUT_FULL", "content": "Output"},
        {"type": "CLI_STDERR", "content": "Error"},
    ]
    assert merge_consecutive_events(events) == events


def test_merge_consecutive_events_mixed_types():
    """Tests a complex sequence of mixed events."""
    events = [
        {"type": "message", "role": "user", "content": "A"},
        {"type": "message", "role": "user", "content": "B"},
        {"type": "tool_use", "tool_name": "tool1"},
        {"type": "CLI_STDOUT_FULL", "content": "Out1"},
        {"type": "CLI_STDOUT_FULL", "content": "Out2"},
        {"type": "message", "role": "ai", "content": "C"},
    ]
    expected = [
        {"type": "message", "role": "user", "content": "A\nB"},
        {"type": "tool_use", "tool_name": "tool1"},
        {"type": "CLI_STDOUT_FULL", "content": "Out1Out2"},
        {"type": "message", "role": "ai", "content": "C"},
    ]
    assert merge_consecutive_events(events) == expected


def test_merge_consecutive_events_non_string_content():
    """Tests that non-string content is safely converted."""
    events = [
        {"type": "message", "role": "user", "content": 123},
        {"type": "message", "role": "user", "content": 456},
    ]
    expected = [{"type": "message", "role": "user", "content": "123\n456"}]
    assert merge_consecutive_events(events) == expected


def test_merge_consecutive_events_tracelogevent_objects():
    """Tests that TraceLogEvent objects are correctly handled and merged."""
    events = [
        TraceLogEvent(type=TraceEventType.MESSAGE, role="user", content="Hello"),
        TraceLogEvent(type=TraceEventType.MESSAGE, role="user", content="World"),
    ]
    merged = merge_consecutive_events(events)
    assert len(merged) == 1
    assert merged[0]["type"] == "message"
    assert merged[0]["role"] == "user"
    assert merged[0]["content"] == "Hello\nWorld"



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
