"""
Benchmark Case 19: Build integrity test for LlmAgent with artifacts.

Description:
  This benchmark tests the ability to create an `LlmAgent` that can reference
  artifacts (e.g., `{artifact.my_data}`) in its instructions.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Can access the data provided in the artifact.
    - Returns the content of the artifact in its response.
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

  artifact_data = {"my_data": "important information"}
  response = await run_agent_test(
      root_agent,
      "What is the data?",
      artifact_data=artifact_data,
      mock_llm_response="important information",
  )
  assert "important information" in response
  assert (
      "{artifact.my_data}" in root_agent.instruction
  ), "Instruction must reference artifact."
  assert root_agent.name == "artifact_agent", "Agent name mismatch."
