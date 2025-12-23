"""
Benchmark Case 21: A minimal LlmAgent with an invalid name.

Description:
  This benchmark tests the ability to fix a ValueError caused by using an invalid
  agent name (containing spaces). The ADK requires agent names to be valid
  identifiers.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent named "my_valid_agent".
"""

import pytest
from google.adk.agents import Agent
from benchmarks.test_helpers import run_agent_test, MODEL_NAME


def test_create_agent_unfixed_fails():
    import unfixed

    # The unfixed code attempts to create an agent with name "my agent",
    # which should raise a ValueError during initialization.
    with pytest.raises(ValueError, match="Agent name must be a valid identifier"):
        unfixed.create_agent(MODEL_NAME)


@pytest.mark.asyncio
async def test_create_agent_passes():
    import fixed

    root_agent = fixed.create_agent(MODEL_NAME)

    assert isinstance(root_agent, Agent), "root_agent should be an instance of Agent"
    assert root_agent.name == "my_valid_agent", "Agent name mismatch."

    response = await run_agent_test(root_agent, "Hello", mock_llm_response="Hello")
    assert "Hello" in response, "Agent should respond to 'Hello' with 'Hello'"
