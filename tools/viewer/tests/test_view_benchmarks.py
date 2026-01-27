"""Test View Benchmarks module."""

import pytest
import json
import yaml
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# --- Global Mock Setup ---
# Must be done before importing the module under test because it imports streamlit at the top level
mock_st = MagicMock()
# Make cache_data a simple pass-through decorator for testing
mock_st.cache_data = lambda func: func
sys.modules["streamlit"] = mock_st

# --- Imports ---
from tools.viewer.view_benchmarks import (
    load_results,
    load_traces,
    load_benchmark_suite,
    load_forensic_data,
    generate_toc_and_inject_anchors,
    ArtifactManager,
    render_diff,
    render_logs,
    _get_concise_error_message,
    merge_consecutive_events,
    get_run_status,
)
from benchmarks.data_models import BenchmarkRunResult, ForensicData, BenchmarkResultType, ExpectedOutcome, TraceLogEvent, TraceEventType

# --- Fixtures ---


@pytest.fixture
def mock_artifact_manager(monkeypatch):
    """Mocks the global artifact_manager to avoid real GCS/FS calls."""
    mock_am = MagicMock(spec=ArtifactManager)
    # Patch the global instance in the module
    import tools.viewer.view_benchmarks as vb

    monkeypatch.setattr(vb, "artifact_manager", mock_am)
    return mock_am


@pytest.fixture
def sample_benchmark_result():
    return BenchmarkRunResult(
        id="test_case_1",
        suite="test_suite",
        benchmark_name="Test Case",
        answer_generator="TestGen",
        status=BenchmarkResultType.PASS,
        result=1,
        answer="print('hello')",
        outcome=ExpectedOutcome.PASS,
    ).model_dump(mode="json")


@pytest.fixture
def sample_forensic_data():
    return {
        "generators": {
            "TestGen": {
                "common_failure_patterns": "Pattern A",
                "critical_anti_patterns": "AntiPattern B",
                "strategic_recommendations": ["Do X", "Do Y"],
            }
        },
        "cases": {},
        "attempts": {},
    }


# --- Section 1: Helper Function Tests ---


def test_get_run_status_completed(tmp_path, monkeypatch):
    """Tests that a run with results.json is marked Completed."""
    run_id = "test_run"
    (tmp_path / run_id).mkdir()
    (tmp_path / run_id / "results.json").write_text("[]")

    # Mock artifact_manager.get_file to use tmp_path
    import tools.viewer.view_benchmarks as vb

    monkeypatch.setattr(
        vb.artifact_manager,
        "get_file",
        lambda rid, fname: tmp_path / rid / fname
        if (tmp_path / rid / fname).exists()
        else None,
    )

    assert get_run_status(run_id) == "Completed"


def test_get_run_status_pending(tmp_path, monkeypatch):
    """Tests that a run with trace.yaml but no results.json is marked Pending."""
    run_id = "test_run_pending"
    (tmp_path / run_id).mkdir()
    (tmp_path / run_id / "trace.yaml").write_text("---")

    import tools.viewer.view_benchmarks as vb

    monkeypatch.setattr(
        vb.artifact_manager,
        "get_file",
        lambda rid, fname: tmp_path / rid / fname
        if (tmp_path / rid / fname).exists()
        else None,
    )

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


# --- Section 2: Loaders & Integration Tests ---


def test_load_results_valid(mock_artifact_manager, tmp_path, sample_benchmark_result):
    """Test loading a valid results.json."""
    run_id = "run_1"
    file_path = tmp_path / "results.json"
    with open(file_path, "w") as f:
        json.dump([sample_benchmark_result], f)

    mock_artifact_manager.get_file.return_value = file_path

    results = load_results(run_id)
    assert len(results) == 1
    assert results[0].id == "test_case_1"
    assert results[0].status == BenchmarkResultType.PASS


def test_load_results_malformed(mock_artifact_manager, tmp_path):
    """Test loading a malformed results.json (should raise Pydantic validation error or JSON error)."""
    run_id = "run_bad"
    file_path = tmp_path / "results.json"
    file_path.write_text("{bad_json")

    mock_artifact_manager.get_file.return_value = file_path

    with pytest.raises(json.JSONDecodeError):
        load_results(run_id)


def test_load_results_invalid_schema(mock_artifact_manager, tmp_path):
    """Test loading a valid JSON that doesn't match the schema."""
    run_id = "run_invalid"
    file_path = tmp_path / "results.json"
    with open(file_path, "w") as f:
        json.dump([{"id": "missing_fields"}], f)

    mock_artifact_manager.get_file.return_value = file_path

    with pytest.raises(Exception):  # Pydantic ValidationError
        load_results(run_id)


def test_load_traces_valid(mock_artifact_manager, tmp_path):
    """Test loading a valid multi-document trace.yaml."""
    run_id = "run_trace"
    file_path = tmp_path / "trace.yaml"
    content = """
data:
  benchmark_name: "Test Case 1"
  trace_logs:
    - type: "message"
      content: "msg1"
---
data:
  benchmark_name: "Test Case 2"
  trace_logs:
    - type: "tool_use"
      content: "tool1"
"""
    file_path.write_text(content)
    mock_artifact_manager.get_file.return_value = file_path

    traces = load_traces(run_id)
    assert len(traces) == 2
    assert "Test Case 1" in traces
    assert len(traces["Test Case 1"]) == 1
    assert traces["Test Case 2"][0]["type"] == "tool_use"


def test_load_traces_empty(mock_artifact_manager, tmp_path):
    """Test loading an empty trace file."""
    run_id = "run_empty"
    file_path = tmp_path / "trace.yaml"
    file_path.write_text("")
    mock_artifact_manager.get_file.return_value = file_path

    traces = load_traces(run_id)
    assert traces == {}


def test_load_forensic_data_valid(
    mock_artifact_manager, tmp_path, sample_forensic_data
):
    """Test loading valid forensic data."""
    run_id = "run_forensic"
    file_path = tmp_path / "forensic_data.json"
    with open(file_path, "w") as f:
        json.dump(sample_forensic_data, f)
    mock_artifact_manager.get_file.return_value = file_path

    data = load_forensic_data(run_id)
    assert isinstance(data, ForensicData)
    assert "TestGen" in data.generators
    assert data.generators["TestGen"].common_failure_patterns == "Pattern A"


def test_generate_toc_and_inject_anchors():
    """Test TOC generation and anchor injection."""
    markdown = """
# Header One
Some text.
## Header Two
More text.
# Header Three
"""
    modified, toc = generate_toc_and_inject_anchors(markdown)

    # Check anchors injected
    assert '<div id="header-one"></div>' in modified
    assert '<div id="header-two"></div>' in modified

    # Check TOC structure
    assert "- [Header One](#header-one)" in toc
    assert "- [Header Two](#header-two)" in toc


def test_render_logs_merging_logic():
    """
    Since we can't easily assert on st.write calls, we verify the data preparation logic inside render_logs.
    """
    # Mocking st methods to ensure they are called
    import tools.viewer.view_benchmarks as vb

    vb.st.container = MagicMock()
    vb.st.expander = MagicMock()

    logs = [
        {"type": "tool_use", "tool_name": "test_tool", "tool_input": {}},
        {"type": "tool_result", "tool_output": "result"},
        {"type": "model_response", "content": "response"},
    ]

    # Should run without error
    render_logs(logs)


def test_load_benchmark_suite_path_resolution(tmp_path):
    """Test that suite loading finds files correctly."""
    # Create a dummy suite
    suite_file = tmp_path / "suite.yaml"
    suite_data = {"benchmarks": [{"id": "case_1", "question": "Q"}]}
    with open(suite_file, "w") as f:
        yaml.dump(suite_data, f)

    # 1. Absolute path
    cases = load_benchmark_suite(str(suite_file))
    assert "case_1" in cases

    # 2. Relative path (mocking os.getcwd)
    with patch("os.getcwd", return_value=str(tmp_path)):
        cases_rel = load_benchmark_suite("suite.yaml")
        assert "case_1" in cases_rel


def test_load_benchmark_suite_jsonl(tmp_path):
    """Test loading JSONL suites."""
    suite_file = tmp_path / "suite.jsonl"
    with open(suite_file, "w") as f:
        f.write('{"id": "case_1", "q": "test"}\n')
        f.write('{"id": "case_2", "q": "test2"}\n')

    cases = load_benchmark_suite(str(suite_file))
    assert len(cases) == 2
    assert "case_1" in cases
    assert "case_2" in cases


def test_artifact_manager_list_runs_local(tmp_path):
    """Test listing runs from local directory."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    (runs_dir / "run_A").mkdir()
    (runs_dir / "run_B").mkdir()
    (runs_dir / "file.txt").touch()  # Should be ignored

    am = ArtifactManager(bucket_name=None, local_dir=runs_dir)
    runs = am.list_runs()

    assert "run_A" in runs
    assert "run_B" in runs
    assert "file.txt" not in runs
    assert len(runs) == 2
