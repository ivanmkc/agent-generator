"""
Benchmark Case 22: A minimal LlmAgent with a logic error.

Description:
  This benchmark tests the ability to fix a logic error where the agent's instruction
  does not meet the requirements (responding with "Hello World!").

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that responds with "Hello World!".
"""

import asyncio

from google.adk.agents import Agent
import pytest

from benchmarks.test_helpers import MODEL_NAME
from benchmarks.test_helpers import run_agent_test


def test_create_agent_unfixed_fails():
  import unfixed

  # Logic error: The agent exists but has the wrong instruction.
  root_agent = unfixed.create_agent(MODEL_NAME)
  # It should NOT have the correct instruction yet
  assert "Hello World!" not in root_agent.instruction


@pytest.mark.asyncio
async def test_create_agent_passes():
  import fixed

  root_agent = fixed.create_agent(MODEL_NAME)

  assert isinstance(
      root_agent, Agent
  ), "root_agent should be an instance of Agent"
  response = await run_agent_test(
      root_agent, "Say hello.", mock_llm_response="Hello World!"
  )
  assert "Hello World!" in response, "Agent should respond with 'Hello World!'"
  assert root_agent.name == "logic_agent", "Agent name mismatch."
