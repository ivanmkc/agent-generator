from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents import SequentialAgent


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates a SequentialAgent that demonstrates inter-agent state management.

  Instructions:
      Create a SequentialAgent named "state_management_coordinator" with two sub-agents:
      1. "writer_agent": Writes the value 'xyz' to the session state key "secret_word".
      2. "reader_agent": Reads the value from "secret_word" and outputs it.

      Requirements:
      - The 'writer' agent should write the value 'xyz' to a key named 'my_value' in the session state.
      - The 'reader' agent should read the value from 'my_value' and the final response must contain 'xyz'.

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of SequentialAgent with state-managing sub-agents.
  """
  writer_agent = LlmAgent(
      name="writer_agent",
      model=model_name,
      instruction=(
          "Your sole task is to output the string 'xyz'. Do not add any other"
          " text."
      ),
      output_key="secret_word",
  )

  reader_agent = LlmAgent(
      name="reader_agent",
      model=model_name,
      instruction=(
          "The secret word is {secret_word}. Your task is to simply repeat that"
          " secret word."
      ),
  )

  root_agent = SequentialAgent(
      name="state_management_coordinator",
      sub_agents=[writer_agent, reader_agent],
  )
  return root_agent
