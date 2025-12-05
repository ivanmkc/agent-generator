"""
Benchmark Case 11: A direct implementation test for InMemoryRunner.

Description:
  This benchmark ensures that a basic `LlmAgent` can be successfully executed
  by the `InMemoryRunner` (which is implicitly used by `run_agent_test`).
  It serves as a baseline integrity check for the runner integration.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Responds to "Hello, runner." with "Hello".
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
      root_agent, "Hello, runner.", mock_llm_response="Hello"
  )
  assert "Hello" in response
  assert root_agent.name == "runnable_agent", "Agent name mismatch."
