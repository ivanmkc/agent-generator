"""
Benchmark Case 08: A simple custom agent with conditional logic.

Description:
  This benchmark tests the ability to create a custom agent (`CustomConditionalAgent`)
  that inherits from `BaseAgent`. The agent decides which sub-agent ('agent_a' or 'agent_b')
  to run based on a session state variable `run_agent_a`.

Test Verification:
  - Verifies that `create_agent` returns a valid custom agent that:
    - Runs `agent_a` when `run_agent_a` is True.
    - Runs `agent_b` when `run_agent_a` is False.
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

  # Test Condition A
  response_a = await run_agent_test(
      root_agent,
      "Run",
      initial_state={"run_agent_a": True},
      mock_llm_response="Agent A",
  )
  assert "Agent A" in response_a

  # Test Condition B
  response_b = await run_agent_test(
      root_agent,
      "Run",
      initial_state={"run_agent_a": False},
      mock_llm_response="Agent B",
  )
  assert "Agent B" in response_b

  assert root_agent.agent_a.name == "agent_a", "Sub-agent A name mismatch."
  assert root_agent.agent_b.name == "agent_b", "Sub-agent B name mismatch."
