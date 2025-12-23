"""
Benchmark Case 07: A root agent delegating a task to a sub-agent.

Description:
  This benchmark tests the ability to create a root `LlmAgent` that can delegate
  a specific task ("I need a specialist") to a sub-agent named 'specialist_agent'.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Has 'specialist_agent' as a sub-agent.
    - Successfully delegates the task.
    - Returns the sub-agent's response ("specialist ok").
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
    response = await run_agent_test(
        root_agent, "I need a specialist.", mock_llm_response="specialist ok"
    )
    assert "specialist ok" in response.lower()

    assert any(
        sub.name == "specialist_agent" for sub in root_agent.sub_agents
    ), "Root agent should have 'specialist_agent' as a sub-agent."
