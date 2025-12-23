"""
Benchmark Case 05: A ParallelAgent running two agents concurrently.

Description:
  This benchmark tests the ability to create a `ParallelAgent`
  that runs two sub-agents concurrently.

Test Verification:
  - Verifies that `create_agent` returns a valid ParallelAgent that:
    - Executes its sub-agents.
    - Returns a response that indicates successful parallel execution (mocked as "parallel").
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
        root_agent, "Run in parallel.", mock_llm_response="parallel"
    )
    assert "parallel" in response.lower()

    from google.adk.agents import ParallelAgent

    assert isinstance(root_agent, ParallelAgent), "Agent should be a ParallelAgent."

    sub_agent_names = [sub.name for sub in root_agent.sub_agents]
    assert "agent_one" in sub_agent_names, "Missing 'agent_one'."
    assert "agent_two" in sub_agent_names, "Missing 'agent_two'."
