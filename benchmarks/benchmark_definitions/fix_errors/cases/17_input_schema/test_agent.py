"""
Benchmark Case 17: Build integrity test for LlmAgent with input_schema.

Description:
  This benchmark tests the ability to create an `LlmAgent` (`worker_agent`) with an
  `input_schema` (`UserInfo`) and expose it as a tool to another agent (`agent`).
  This verifies structured input validation and tool usage.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Can process structured input via the worker agent.
    - Correctly handles input matching the schema.
    - Correctly handles (or fails on) invalid input.
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

  # Valid input test
  response = await run_agent_test(
      root_agent,
      "Process this info: name is Alice, age is 30",
      mock_llm_response='{"name": "Alice", "age": 30}',
  )
  assert "Alice" in response and "30" in response

  # Invalid input test
  response_invalid = await run_agent_test(
      root_agent,
      "Process this info: name is Bob",
      mock_llm_response="Error: The field 'age' is missing.",
  )
  assert "age" in response_invalid.lower()

  worker_agent = next(
      (
          t.agent
          for t in root_agent.tools
          if hasattr(t, "agent") and t.agent.name == "worker"
      ),
      None,
  )
  assert worker_agent is not None, "Worker agent tool not found."
  assert (
      worker_agent.input_schema is not None
  ), "Worker agent needs an input_schema."

  schema_fields = worker_agent.input_schema.model_fields
  assert "name" in schema_fields, "Schema missing 'name' field."
  assert "age" in schema_fields, "Schema missing 'age' field."
