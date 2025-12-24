# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions for benchmarks."""

import itertools
import json
from typing import Any

from benchmarks.data_models import TraceLogEvent, TraceEventType


def permute(cls, **kwargs):
    """Helper to generate permutations of class instances.

    Args:
        cls: The class to instantiate.
        **kwargs: Dictionary where keys are argument names and values are lists of possible values.

    Yields:
        Instances of cls with all combinations of arguments.
    """
    keys = kwargs.keys()
    values = kwargs.values()
    for instance_values in itertools.product(*values):
        yield cls(**dict(zip(keys, instance_values)))


def parse_cli_stream_json_output(
    stdout_str: str,
) -> tuple[dict[str, Any], list[TraceLogEvent]]:
    """Parses the NDJSON output from the Gemini CLI in stream-json format.

    Args:
        stdout_str: The raw stdout string from the CLI.

    Returns:
        A tuple containing:
        - A dictionary with the parsed response (e.g., {"response": "...", "stats": "..."}).
        - A list of TraceLogEvent objects.
    """
    response_dict = {"response": ""}
    logs: list[TraceLogEvent] = []

    for line in stdout_str.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            event_type = event.get("type")
            event_data = event.get("data", event)

            # Map event_type to TraceEventType enum if it's one of the recognized types
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
                enum_type = TraceEventType.ADK_EVENT # Default to generic ADK_EVENT

            log_event = TraceLogEvent(
                type=enum_type, source="cli_stream", details=event
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
                TraceLogEvent(type=TraceEventType.CLI_STDOUT_RAW, source="cli_stream", content=line)
            )
    return response_dict, logs
