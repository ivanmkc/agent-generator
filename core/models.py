"""
Core Data Models.

This module contains shared Pydantic models used across the benchmarks runner, 
tools, and analysis scripts.
"""

import enum
from typing import Any, Optional, Union, List
from pydantic import BaseModel, Field

class TraceEventType(str, enum.Enum):
    """
    Predefined types for trace log events.
    """

    ADK_EVENT = "ADK_EVENT"  # Generic ADK event if more specific type not inferred
    MESSAGE = "message"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    GEMINI_API_RESPONSE = "GEMINI_API_RESPONSE"
    INIT = "init"
    CLI_STDOUT_FULL = "CLI_STDOUT_FULL"  # Full stdout from CLI call
    CLI_STDOUT_RAW = "CLI_STDOUT_RAW"  # Raw stdout from CLI call if not stream-json
    CLI_STDERR = "CLI_STDERR"
    GEMINI_CLIENT_ERROR = "GEMINI_CLIENT_ERROR"
    SYSTEM_RESULT = "system_result"  # Internal system result like stats
    RUN_START = "run_start"
    RUN_END = "run_end"


class TraceLogEvent(BaseModel):
    """Represents a single event in the trace logs."""

    type: TraceEventType = Field(
        ...,
        description=("The type of event (e.g., 'tool_use', 'model_response')."),
    )
    timestamp: Optional[str] = Field(
        None, description="The ISO 8601 timestamp of the event."
    )
    source: str = Field(
        "unknown", description="The source of the event (e.g., 'docker', 'adk')."
    )
    role: Optional[str] = Field(
        None,
        description="The role associated with the event (user/model/system).",
    )
    author: Optional[str] = Field(
        None, description="The name of the agent or entity that produced the event."
    )
    tool_name: Optional[str] = Field(None, description="Name of the tool used.")
    tool_call_id: Optional[str] = Field(
        None, description="Unique identifier for the tool call."
    )
    tool_input: Optional[dict[str, Any]] = Field(
        None, description="Arguments provided to the tool."
    )
    tool_output: Optional[str] = Field(
        None, description="Output/result returned from the tool."
    )
    content: Union[str, dict[str, Any], list[Any], None] = Field(
        None, description="The primary content of the event."
    )
    details: Optional[dict[str, Any]] = Field(
        None,
        description=("Additional details about the event, as a flexible dictionary."),
    )
