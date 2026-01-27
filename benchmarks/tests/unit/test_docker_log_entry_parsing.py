"""Test Docker Log Entry Parsing module."""

from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError
import pytest


class DockerLogEntry(BaseModel):
    """Represents a single log entry from the Docker CLI output."""

    type: str
    tool_name: Optional[str] = None


def test_docker_tool_use_log_entry_parsing():
    """
    Tests that a DOCKER_CLI_STDOUT log entry containing a tool_use JSON
    is correctly parsed by the DockerLogEntry Pydantic model.
    """
    log_content = (
        '{"type":"tool_use","timestamp":"2025-12-01T14:53:22.030Z","tool_name":"codebase_investigator","tool_id":"codebase_investigator-1764600802030-e5b5ee36c84aa","parameters":{"objective":"Find'
        " the base class for all agents in `google.adk.agents` within the"
        ' `adk-python/src/google/adk/` directory."}}'
    )

    parsed_entry = DockerLogEntry.model_validate_json(log_content)

    assert parsed_entry.type == "tool_use"
    assert parsed_entry.tool_name == "codebase_investigator"
    assert parsed_entry.tool_name is not None


def test_docker_other_log_entry_parsing():
    """
    Tests that a DOCKER_CLI_STDOUT log entry with a different type
    is correctly parsed by the DockerLogEntry Pydantic model,
    and tool_name remains None.
    """
    log_content = (
        '{"type":"message","timestamp":"2025-12-01T14:53:19.445Z","role":"user","content":"Some'
        ' user message"}'
    )

    parsed_entry = DockerLogEntry.model_validate_json(log_content)

    assert parsed_entry.type == "message"
    assert parsed_entry.tool_name is None


def test_invalid_json_parsing():
    """
    Tests that invalid JSON content raises a ValidationError.
    """
    invalid_log_content = "This is not valid JSON"

    with pytest.raises((ValidationError, ValueError)):
        DockerLogEntry.model_validate_json(invalid_log_content)


def test_json_without_tool_name_parsing():
    """
    Tests that JSON content without 'tool_name' but with 'type' is parsed
    correctly, with tool_name being None.
    """
    log_content = '{"type":"init","timestamp":"2025-12-01T14:53:19.444Z","session_id":"72cda94a-a3d9-4a7a-81fe-e7a96077d2de","model":"gemini-2.5-flash"}'

    parsed_entry = DockerLogEntry.model_validate_json(log_content)

    assert parsed_entry.type == "init"
    assert parsed_entry.tool_name is None
