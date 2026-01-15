"""
Benchmark Case 23: A minimal LlmAgent with a missing import.

Description:
  This benchmark tests the ability to fix a `NameError` caused by a missing import
  of `LlmAgent`.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent.
"""

import asyncio

from google.adk.agents import Agent
import pytest

from benchmarks.test_helpers import MODEL_NAME
from benchmarks.test_helpers import run_agent_test


def test_create_agent_unfixed_fails():
  import unfixed

  with pytest.raises(NameError):
    unfixed.create_agent(MODEL_NAME)


@pytest.mark.asyncio
async def test_create_agent_passes():
  import fixed

  root_agent = fixed.create_agent(MODEL_NAME)

  assert isinstance(
      root_agent, Agent
  ), "root_agent should be an instance of Agent"
  response = await run_agent_test(
      root_agent, "Hello", mock_llm_response="Hello"
  )
  assert "Hello" in response
  assert root_agent.name == "import_agent", "Agent name mismatch."
