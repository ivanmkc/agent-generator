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

"""Reusable components for build integrity test snippets."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import patch

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel
from pydantic import Field

MODEL_NAME = "gemini-2.5-flash"


def basic_tool(query: str) -> str:
    """A simple tool that returns a fixed string."""
    return f"The tool received the query: {query}"


class BasicOutputSchema(BaseModel):
    """A basic Pydantic model for testing output_schema."""

    field_one: str = Field(description="The first field.")
    field_two: int = Field(description="The second field.")


def create_basic_llm_agent(name: str, instruction: str) -> LlmAgent:
    """Creates a simple LlmAgent with a default model."""
    return LlmAgent(name=name, model=MODEL_NAME, instruction=instruction)


async def run_agent_test(
    agent: BaseAgent,
    input_message: str,
    initial_state: dict[str, Any] | None = None,
    artifact_data: dict[str, str] | None = None,
    mock_llm_response: str | None = "This is a mocked response.",
    expect_response: bool = True,
) -> str:
    """Runs a test against a given agent and returns the final response."""
    # Patch the Client class where it is imported in the code or globally
    with patch("google.genai.Client") as mock_client_cls:
        if mock_llm_response:
            # Configure the mock client instance
            mock_client_instance = mock_client_cls.return_value

            # Create a mock response object matching the expected structure
            mock_response = types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            parts=[types.Part(text=mock_llm_response)], role="model"
                        )
                    )
                ]
            )

            # Mock the async generate_content method
            # Note: We need to mock the chain .aio.models.generate_content
            mock_client_instance.aio.models.generate_content = AsyncMock(
                return_value=mock_response
            )

        app = App(name=f"test_app_{agent.name}", root_agent=agent)
        runner = InMemoryRunner(app=app)

        session = await runner.session_service.create_session(
            app_name=app.name, user_id="test-user", state=initial_state or {}
        )

        if artifact_data:
            for filename, value in artifact_data.items():
                await runner.artifact_service.save_artifact(
                    app_name=app.name,
                    user_id="test-user",
                    session_id=session.id,
                    filename=filename,
                    artifact=types.Part(text=value),
                )

        final_response = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(
                role="user", parts=[types.Part(text=input_message)]
            ),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                text_parts = [
                    part.text
                    for part in event.content.parts
                    if hasattr(part, "text") and part.text is not None
                ]
                if text_parts:
                    final_response = "".join(text_parts)

                tool_parts = [
                    part.function_call.name
                    for part in event.content.parts
                    if hasattr(part, "function_call") and part.function_call is not None
                ]
                if tool_parts:
                    final_response = "".join(tool_parts)

        if expect_response:
            assert (
                final_response
            ), f"Agent {agent.name} produced an empty final response."
        return final_response
