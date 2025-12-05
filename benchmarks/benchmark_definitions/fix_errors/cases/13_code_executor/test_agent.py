"""
Benchmark Case 13: An LlmAgent with a BuiltInCodeExecutor.

Description:
  This benchmark tests the ability to create an `LlmAgent` equipped with a
  `BuiltInCodeExecutor`, allowing it to execute Python code.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Has a code executor configured.
    - Can execute code to solve a problem (2 + 2).
    - Returns the correct result (4).
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
      root_agent, "Calculate 2 + 2.", mock_llm_response="4"
  )
  assert "4" in response

  from google.adk.code_executors.built_in_code_executor import BuiltInCodeExecutor

  assert isinstance(
      root_agent.code_executor, BuiltInCodeExecutor
  ), "Agent should have a BuiltInCodeExecutor."
  assert root_agent.name == "code_exec_agent", "Agent name mismatch."
