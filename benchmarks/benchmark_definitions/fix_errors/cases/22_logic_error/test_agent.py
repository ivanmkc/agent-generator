"""
Benchmark Case 22: Implementing a custom LogicAgent from scratch.

Description:
  This benchmark tests the ability to implement a custom agent class that inherits
  from LlmAgent but implements custom deterministic logic instead of using an LLM.

Test Verification:
  - Verifies that `create_agent` returns a valid LogicAgent (subclass of LlmAgent).
  - Verifies that the agent responds with "Hello World!" to "Say hello.".
  - Verifies that the agent responds with "Goodbye!" to other inputs.
"""

import asyncio

from google.adk.agents import BaseAgent
import pytest

from benchmarks.test_helpers import MODEL_NAME
from benchmarks.test_helpers import run_agent_test


def test_create_agent_unfixed_raises_error():
    import unfixed

    # The unfixed version should raise NotImplementedError
    with pytest.raises(NotImplementedError):
        unfixed.create_agent(MODEL_NAME)


@pytest.mark.asyncio
async def test_create_agent_passes():
    import fixed

    root_agent = fixed.create_agent(MODEL_NAME)

    assert isinstance(
        root_agent, BaseAgent
    ), "root_agent should be an instance of Agent"

    # Verify positive case
    response = await run_agent_test(
        root_agent, "Say hello.", mock_llm_response="Hello World!"
    )
    assert "Hello World!" in response, "Agent should respond with 'Hello World!'"
    assert root_agent.name == "logic_agent", "Agent name mismatch."

    # Verify negative case
    response_negative = await run_agent_test(
        root_agent, "Something else", mock_llm_response="Goodbye!"
    )
    assert (
        "Goodbye!" in response_negative
    ), "Agent should respond with 'Goodbye!' for other inputs."
