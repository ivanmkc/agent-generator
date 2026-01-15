"""
Benchmark Case 16: Build integrity test for LlmAgent with generate_content_config.

Description:
  This benchmark tests the ability to configure model generation parameters (like temperature)
  using `generate_content_config` on an `LlmAgent`.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Has the configuration set.
    - Responds as instructed ("Hello world!").
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
      root_agent, "Say hello.", mock_llm_response="Hello world!"
  )
  assert "Hello world!" in response
  assert (
      root_agent.generate_content_config.temperature == 0.0
  ), "Temperature should be 0.0."
  assert root_agent.name == "config_agent", "Agent name mismatch."
