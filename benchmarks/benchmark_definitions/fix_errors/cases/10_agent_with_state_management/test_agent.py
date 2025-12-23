"""
Benchmark Case 10: An agent that writes to and reads from session.state.

Description:
  This benchmark tests the ability to coordinate state between agents using `output_key`
  and dynamic instruction placeholders.
  - `writer_agent` writes 'xyz' to `session.state["secret_word"]`.
  - `reader_agent` reads `secret_word` from state using `{secret_word}` in its instruction.

Test Verification:
  - Verifies that `create_agent` returns a valid SequentialAgent that:
    - Successfully passes the state from writer to reader.
    - Returns the correct secret word ("xyz") in the final response.
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
    response = await run_agent_test(root_agent, "Start", mock_llm_response="xyz")
    assert "xyz" in response.lower()

    from google.adk.agents import SequentialAgent

    assert isinstance(root_agent, SequentialAgent), "Agent should be a SequentialAgent."
    writer = next((a for a in root_agent.sub_agents if a.name == "writer_agent"), None)
    assert writer is not None, "Writer agent not found."
    assert writer.output_key == "secret_word", "Writer should write to 'secret_word'."
