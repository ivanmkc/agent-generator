"""
Benchmark Case 04: A SequentialAgent orchestrating two simple agents.

Description:
  This benchmark tests the ability to create a `SequentialAgent`
  that orchestrates two sub-agents ('agent_one' and 'agent_two') in a fixed order.

Test Verification:
  - Verifies that `create_agent` returns a valid SequentialAgent that:
    - Runs the sequence of agents.
    - Returns the final response from the last agent in the chain ("two").
"""

import pytest

from benchmarks.test_helpers import MODEL_NAME
from benchmarks.test_helpers import run_agent_test


def test_create_agent_unfixed_fails():
  import unfixed

  with pytest.raises(
      NotImplementedError, match="Agent implementation incomplete."
  ):
    unfixed.create_agent(MODEL_NAME)


@pytest.mark.asyncio
async def test_create_agent_passes():
  import fixed

  root_agent = fixed.create_agent(MODEL_NAME)
  response = await run_agent_test(
      root_agent, "Run the sequence.", mock_llm_response="two"
  )
  assert "two" in response.lower()

  from google.adk.agents import SequentialAgent

  assert isinstance(
      root_agent, SequentialAgent
  ), "Agent should be a SequentialAgent."
  assert len(root_agent.sub_agents) == 2, "Agent should have 2 sub-agents."

  sub_names = [sub.name for sub in root_agent.sub_agents]
  assert "agent_one" in sub_names, "Missing 'agent_one'."
  assert "agent_two" in sub_names, "Missing 'agent_two'."
