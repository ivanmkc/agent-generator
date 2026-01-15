"""
Benchmark Case 25: A SequentialAgent with an interaction error.

Description:
  This benchmark tests the ability to fix a multi-agent interaction error where
  the consumer agent (`reader_agent`) fails to receive data from the producer agent (`writer_agent`)
  because the producer did not set the correct `output_key` in the session state.

Test Verification:
  - Verifies that `create_agent` returns a valid SequentialAgent that:
    - Writer outputs to "correct_key".
    - Reader reads from "correct_key".
    - Final response contains "secret_message".
"""

import asyncio

from google.adk.agents import BaseAgent
import pytest

from benchmarks.test_helpers import MODEL_NAME
from benchmarks.test_helpers import run_agent_test


def test_create_agent_unfixed_fails():
  import unfixed

  # Interaction error: output_key is missing
  root_agent = unfixed.create_agent(MODEL_NAME)
  writer = next(
      (sub for sub in root_agent.sub_agents if sub.name == "writer_agent"), None
  )
  assert writer is not None
  assert writer.output_key != "correct_key"


@pytest.mark.asyncio
async def test_create_agent_passes():
  import fixed

  root_agent = fixed.create_agent(MODEL_NAME)

  assert isinstance(
      root_agent, BaseAgent
  ), "root_agent should be an instance of BaseAgent"

  response = await run_agent_test(
      root_agent, "Start interaction", mock_llm_response="secret_message"
  )
  assert (
      "secret_message" in response
  ), "Reader agent should output 'secret_message'"

  # Verify structural fix: writer should have output_key set
  writer = next(
      (sub for sub in root_agent.sub_agents if sub.name == "writer_agent"), None
  )
  assert writer is not None, "writer_agent not found."
  assert (
      writer.output_key == "correct_key"
  ), "writer_agent should write to 'correct_key'."
