"""
Benchmark Case 15: An LlmAgent with an after_model_callback.

Description:
  This benchmark tests the ability to attach an `after_model_callback` to an `LlmAgent`.
  The callback should be executed after the model responds and modify the output.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Responds to a greeting.
    - The response contains the text appended by the callback.
"""

import pytest

from benchmarks.test_helpers import MODEL_NAME
from benchmarks.test_helpers import run_agent_test


def test_create_agent_unfixed_fails():
    import unfixed

    with pytest.raises(NotImplementedError, match="Agent implementation incomplete."):
        unfixed.create_agent(MODEL_NAME)


@pytest.mark.asyncio
async def test_create_agent_passes():
    import fixed

    root_agent = fixed.create_agent(MODEL_NAME)
    # Mock response doesn't need the modification; the callback will add it.
    response = await run_agent_test(
        root_agent, "Hello", mock_llm_response="Hello world"
    )

    assert "Hello" in response or "Hi" in response
    assert (
        "(modified by callback)" in response
    ), "The response was not modified by the callback."
    assert (
        root_agent.after_model_callback is not None
    ), "Agent should have an after_model_callback."
    assert root_agent.name == "callback_agent", "Agent name mismatch."
