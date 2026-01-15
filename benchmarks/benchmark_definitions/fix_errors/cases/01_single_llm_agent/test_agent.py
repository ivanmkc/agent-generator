"""
Benchmark Case 01: A minimal LlmAgent.

Description:
  This benchmark tests the ability to create a minimal LlmAgent named 'single_agent'.
  The agent is expected to respond to a simple greeting.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Is named 'single_agent'.
    - Responds to "Hello" with a string containing "Hello".
"""

import pytest

from benchmarks.test_helpers import MODEL_NAME
from benchmarks.test_helpers import run_agent_test


def test_create_agent_unfixed_fails():
  import unfixed

  if unfixed is None:
    pytest.fail("Could not import agent module.")
  with pytest.raises(
      NotImplementedError, match="Agent implementation incomplete."
  ):
    unfixed.create_agent(MODEL_NAME)


@pytest.mark.asyncio
async def test_create_agent_passes():
  import fixed

  if fixed is None:
    pytest.fail("Could not import agent module.")

  # Create the agent using the function
  root_agent = fixed.create_agent(MODEL_NAME)

  # Run the verification using standard helper
  response = await run_agent_test(
      root_agent, "Hello", mock_llm_response="Hello"
  )

  # Assertions
  print(f"Agent response: {response}")
  assert "Hello" in response, "Expected a greeting containing 'Hello'."
  assert root_agent.name == "single_agent", "Agent name mismatch."
