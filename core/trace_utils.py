"""
Core Trace Utilities.

This module provides utilities for parsing and manipulating trace logs.
"""

import json
from typing import Any, List, Dict, Tuple
from core.models import TraceLogEvent, TraceEventType

def deduplicate_trace_logs(logs: List[TraceLogEvent]) -> List[TraceLogEvent]:
    """Removes redundant information from trace logs to save space without data loss.

    Specifically:
    1. Removes the 'details' field from TOOL_RESULT events.
    2. Truncates large context in GEMINI_CLIENT_ERROR events (context is redundant with trace history).

    Args:
        logs: The list of TraceLogEvent objects to deduplicate.

    Returns:
        The deduplicated list of logs.
    """
    if not logs:
        return []

    for log in logs:
        # 1. Deduplicate TOOL_RESULT:
        # The 'details' field usually contains the raw JSON event from the CLI.
        # Since we've already extracted the 'output' into 'log.tool_output', 
        # 'details' is a 100% redundant copy of the data.
        if log.type == TraceEventType.TOOL_RESULT:
            log.details = None

        # 2. Deduplicate GEMINI_CLIENT_ERROR:
        # These events often contain a 2MB+ 'context' field which is a dump of the
        # entire conversation history (including previous huge tool outputs).
        # Since this history is already captured by previous events in the trace,
        # we truncate the 'context' payloads while keeping the error message.
        if log.type == TraceEventType.GEMINI_CLIENT_ERROR and isinstance(log.content, str):
            # Only attempt if content is suspiciously large (e.g. > 100KB)
            if len(log.content) > 100000:
                try:
                    data = json.loads(log.content)
                    if "context" in data and isinstance(data["context"], list):
                        modified = False
                        for msg in data["context"]:
                            # Truncate function responses in the error context
                            # The full response is already in the TOOL_RESULT event
                            parts = msg.get("parts", [])
                            if isinstance(parts, list):
                                for part in parts:
                                    if "functionResponse" in part:
                                        fr = part["functionResponse"]
                                        resp = fr.get("response", {})
                                        if "output" in resp and len(str(resp["output"])) > 1000:
                                            resp["output"] = "<TRUNCATED_SEE_TOOL_RESULT_EVENT>"
                                            modified = True
                                    # Also truncate huge text parts if they are likely file contents
                                    if "text" in part and len(part["text"]) > 5000:
                                        part["text"] = part["text"][:5000] + "... <TRUNCATED_CONTEXT>"
                                        modified = True
                        
                        if modified:
                            log.content = json.dumps(data)
                except (json.JSONDecodeError, AttributeError):
                    pass # Keep original if parsing fails

    return logs


def parse_cli_stream_json_output(
    stdout_str: str,
) -> Tuple[Dict[str, Any], List[TraceLogEvent]]:
    """Parses the NDJSON output from the Gemini CLI in stream-json format.

    Args:
        stdout_str: The raw stdout string from the CLI.

    Returns:
        A tuple containing:
        - A dictionary with the parsed response (e.g., {"response": "...", "stats": "..."}).
        - A list of TraceLogEvent objects.
    """
    response_dict = {"response": ""}
    logs: List[TraceLogEvent] = []

    for line in stdout_str.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            event_type = event.get("type")
            event_data = event.get("data", event)

            # Map event_type to TraceEventType enum if it's one of the recognized types
            # TODO: Use polymorphism for cleaner mapping
            if event_type == "init":
                enum_type = TraceEventType.INIT
            elif event_type == "message":
                enum_type = TraceEventType.MESSAGE
            elif event_type == "tool_use":
                enum_type = TraceEventType.TOOL_USE
            elif event_type == "tool_result":
                enum_type = TraceEventType.TOOL_RESULT
            elif event_type == "result":
                enum_type = TraceEventType.SYSTEM_RESULT
            else:
                enum_type = TraceEventType.ADK_EVENT  # Default to generic ADK_EVENT

            # Avoid storing 'details' for tool_result to prevent duplication of huge outputs
            details = None if enum_type == TraceEventType.TOOL_RESULT else event

            log_event = TraceLogEvent(
                type=enum_type, source="cli_stream", details=details
            )

            if event_type == "message":
                role = event_data.get("role")
                content = event_data.get("content")
                log_event.role = role
                log_event.content = content

                if role in ["model", "assistant"]:
                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and "text" in part:
                                response_dict["response"] += part["text"]
                    elif isinstance(content, str):
                        response_dict["response"] += content

            elif event_type == "tool_use":
                log_event.tool_name = event_data.get("tool_name")
                log_event.tool_call_id = event_data.get("tool_id")
                log_event.tool_input = event_data.get("parameters")

            elif event_type == "tool_result":
                log_event.tool_call_id = event_data.get("tool_id")
                log_event.tool_output = str(event_data.get("output"))

            elif event_type == "result":
                # This is already handled by enum_type = TraceEventType.SYSTEM_RESULT
                if "stats" in event_data:
                    response_dict["stats"] = event_data["stats"]
                    log_event.content = event_data["stats"]

            logs.append(log_event)

        except json.JSONDecodeError:
            logs.append(
                TraceLogEvent(
                    type=TraceEventType.CLI_STDOUT_RAW,
                    source="cli_stream",
                    content=line,
                )
            )
    return response_dict, logs