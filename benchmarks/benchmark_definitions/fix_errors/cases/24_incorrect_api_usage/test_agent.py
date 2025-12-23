"""
Benchmark Case 24: A minimal LlmAgent with an incorrect API usage.

Description:
  This benchmark tests the ability to fix a `ValidationError` caused by passing an
  incorrect argument (`instructions` instead of `instruction`) to the `LlmAgent` constructor.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent.
"""

import asyncio

from google.adk.agents import Agent
from pydantic import ValidationError
import pytest

from benchmarks.test_helpers import MODEL_NAME
from benchmarks.test_helpers import run_agent_test


def test_create_agent_unfixed_fails():
    import unfixed

    with pytest.raises(ValidationError):
        unfixed.create_agent(MODEL_NAME)


@pytest.mark.asyncio
async def test_create_agent_passes():
    import fixed

    root_agent = fixed.create_agent(MODEL_NAME)

    assert isinstance(root_agent, Agent), "root_agent should be an instance of Agent"
    response = await run_agent_test(root_agent, "Hello", mock_llm_response="Hello")
    assert "Hello" in response

    # Verify that the instruction was correctly set (this confirms the API usage fix)
    assert (
        "helpful assistant" in root_agent.instruction
    ), "Instruction attribute not set correctly."
