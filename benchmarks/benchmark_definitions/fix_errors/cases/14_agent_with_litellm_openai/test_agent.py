"""
Benchmark Case 14: An LlmAgent using an OpenAI model via LiteLlm.

Description:
  This benchmark tests the ability to create an `LlmAgent` that uses a third-party
  model (OpenAI's GPT-3.5) via the `LiteLlm` integration.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Is configured with `LiteLlm`.
    - Responds to a greeting (mocked response).
"""

import os

import pytest

from benchmarks.test_helpers import run_agent_test


def test_create_agent_unfixed_fails():
    import unfixed

    with pytest.raises(NotImplementedError, match="Agent implementation incomplete."):
        unfixed.create_agent("gemini-2.5-flash")


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY is not set."
)
@pytest.mark.asyncio
async def test_create_agent_passes():
    import fixed

    root_agent = fixed.create_agent("gemini-2.5-flash")
    response = await run_agent_test(root_agent, "Hello")
    assert "Hello" in response

    from google.adk.models.lite_llm import LiteLlm

    assert isinstance(root_agent.model, LiteLlm), "Agent should use LiteLlm."
    assert "openai" in root_agent.model.model, "Model name should contain 'openai'."

    # TODO: Add more detailed checks on LiteLlm configuration
