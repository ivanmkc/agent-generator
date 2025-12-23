"""
Benchmark Case 06: A LoopAgent that runs a sub-agent a fixed number of times.

Description:
  This benchmark tests the ability to create a `LoopAgent`
  that runs a single sub-agent ('looper_agent') for a fixed number of iterations.

Test Verification:
  - Verifies that `create_agent` returns a valid LoopAgent that:
    - Runs the loop.
    - Returns a response indicative of the loop's execution (mocked as "Iteration 1 complete").
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
        root_agent, "Run the loop.", mock_llm_response="Iteration 1 complete."
    )
    assert "Iteration" in response or "loop" in response.lower()

    from google.adk.agents import LoopAgent

    assert isinstance(root_agent, LoopAgent), "Agent should be a LoopAgent."
    assert root_agent.max_iterations == 2, "Agent should run for 2 iterations."

    # Verify sub-agent name
    # LoopAgent usually has a 'body' or 'sub_agents' depending on implementation details in ADK.
    # Assuming standard BaseAgent structure where children are in sub_agents or it wraps a single agent.
    # If LoopAgent wraps a single agent, we check that.
    # Based on other tests, we iterate sub_agents.
    assert any(
        sub.name == "looper_agent" for sub in root_agent.sub_agents
    ), "Missing 'looper_agent'."
