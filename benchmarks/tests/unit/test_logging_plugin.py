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

"""Tests for the TraceCollectorPlugin."""

import pytest
from unittest.mock import AsyncMock

from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai.types import UsageMetadata

from benchmarks.answer_generators.adk_answer_generator import TraceCollectorPlugin
from benchmarks.data_models import TraceEventType


# A simple tool for the test agent to call
def simple_test_tool(query: str) -> str:
    """A simple tool that returns a fixed string."""
    return f"Response for '{query}'"


class MockLlm(BaseLlm):
    """
    A mock LLM that returns a tool call on the first request and a final text
    response on the second, mimicking a real tool-using flow.
    """

    call_count: int = 0

    async def generate_content_async(self, request, **kwargs):
        self.call_count += 1

        if self.call_count == 1:
            # First call: Request the tool.
            tool_call = types.Part(
                function_call=types.FunctionCall(
                    name="simple_test_tool",
                    args={"query": "test_query"},
                    id="tool_call_1234",
                )
            )
            content = types.Content(parts=[tool_call], role="model")
            usage = types.GenerateContentResponseUsageMetadata(
                prompt_token_count=10,
                candidates_token_count=5,
                total_token_count=15,
            )
        else:
            # Second call: Provide the final text response.
            final_text = types.Part(text="Okay, the tool has been called.")
            content = types.Content(parts=[final_text], role="model")
            usage = types.GenerateContentResponseUsageMetadata(
                prompt_token_count=20,  # Represents tool result in context
                candidates_token_count=8,
                total_token_count=28,
            )

        # The mock must yield two responses for a non-streaming call:
        # 1. The partial=True response (can be empty)
        # 2. The final partial=False response with the full content.
        yield LlmResponse(content=content, usage_metadata=usage, partial=True)
        yield LlmResponse(content=content, usage_metadata=usage, partial=False)


@pytest.mark.asyncio
async def test_trace_collector_plugin_captures_events():
    """
    Tests that the TraceCollectorPlugin correctly captures MESSAGE, TOOL_USE,
    and TOOL_RESULT events in a format compatible with the Benchmark Viewer.
    """
    # 1. Setup
    collector = TraceCollectorPlugin()
    mock_llm = MockLlm(model="mock-model")
    test_agent = LlmAgent(
        name="test_agent",
        model=mock_llm,
        tools=[FunctionTool(simple_test_tool)],
        instruction="Use the tool.",
    )
    app = App(name="test_app", root_agent=test_agent, plugins=[collector])
    runner = InMemoryRunner(app=app)

    # Pre-create the session to avoid lookup errors in the test environment
    await runner.session_service.create_session(
        app_name=app.name, user_id="test_user", session_id="test_session"
    )

    # 2. Execute a run
    initial_prompt = "Use your tool now."
    new_message = types.UserContent(parts=[types.Part(text=initial_prompt)])

    async for event in runner.run_async(
        user_id="test_user", session_id="test_session", new_message=new_message
    ):
        # We don't need to inspect the live events, just the final collected logs
        pass

    collector.finalize()  # Finalize to capture last agent's timing

    # 3. Assertions
    logs = collector.logs

    assert len(logs) > 0, "Collector should have captured logs."

    # Verify that key events were captured
    event_types = [log.type for log in logs]
    assert TraceEventType.MESSAGE in event_types
    assert TraceEventType.TOOL_USE in event_types
    assert TraceEventType.TOOL_RESULT in event_types

    # Verify MESSAGE event content
    message_event = next(
        (
            log
            for log in logs
            if log.type == TraceEventType.MESSAGE and log.role == "user"
        ),
        None,
    )
    assert message_event is not None
    assert message_event.author == "user"
    assert initial_prompt in message_event.content

    # Verify TOOL_USE event content
    tool_use_event = next(
        (log for log in logs if log.type == TraceEventType.TOOL_USE), None
    )
    assert tool_use_event is not None
    assert tool_use_event.tool_name == "simple_test_tool"
    assert tool_use_event.tool_input == {"query": "test_query"}
    assert tool_use_event.tool_call_id == "tool_call_1234"
    assert tool_use_event.author == "test_agent"

    # Verify TOOL_RESULT event content
    tool_result_event = next(
        (log for log in logs if log.type == TraceEventType.TOOL_RESULT), None
    )
    assert tool_result_event is not None
    assert tool_result_event.tool_name == "simple_test_tool"
    assert tool_result_event.tool_output == "Response for 'test_query'"
    assert tool_result_event.tool_call_id == "tool_call_1234"

    # Verify usage metadata was collected
    assert collector.total_prompt_tokens == 30
    assert collector.total_completion_tokens == 13
    assert collector.total_tokens == 43

    # Verify agent execution timing was captured
    assert len(collector.execution_sequence) > 0
    test_agent_timing = next(
        (
            item
            for item in collector.execution_sequence
            if item["agent"] == "test_agent"
        ),
        None,
    )
    assert test_agent_timing is not None
    assert test_agent_timing["duration"] > 0
    assert test_agent_timing["prompt_tokens"] == 30
    assert test_agent_timing["completion_tokens"] == 13
