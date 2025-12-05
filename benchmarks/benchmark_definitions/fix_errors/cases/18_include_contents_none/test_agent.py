"""
Benchmark Case 18: Build integrity test for LlmAgent with include_contents='none'.

Description:
  This benchmark tests the ability to create a stateless `LlmAgent` by setting
  `include_contents="none"`. This ensures the agent does not retain context
  from previous turns.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Is stateless.
    - Responds to the first question.
    - Fails to recall the first question in the second turn.
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

  # First turn: Agent should introduce itself
  response1 = await run_agent_test(
      root_agent, "What is your name?", mock_llm_response="StatelessBot"
  )
  assert "StatelessBot" in response1

  # Second turn: Agent should confirm its stateless nature and not recall the specific previous question.
  response2 = await run_agent_test(
      root_agent,
      "Do you remember what I asked you before?",
      mock_llm_response="I am stateless. I do not remember.",
  )
  assert "stateless" in response2.lower()
  assert "remember" in response2.lower()
  assert "what is your name" not in response2.lower()
  assert root_agent.name == "stateless_agent", "Agent name mismatch."
  assert (
      root_agent.include_contents == "none"
  ), "Agent should be stateless (include_contents='none')."
