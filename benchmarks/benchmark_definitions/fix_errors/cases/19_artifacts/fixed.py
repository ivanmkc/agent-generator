from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates an LlmAgent that tells the user what is the value of `my_data` from artifacts.

  Instructions:
      Create an LlmAgent named "artifact_agent" that tells the user what is the value of `my_data` from artifacts.

      Requirements:
      - The agent's instruction should reference an artifact named 'my_data'.
      - The agent should directly state the content of the 'my_data' artifact in its response.

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of LlmAgent capable of using artifact data.
  """
  agent = LlmAgent(
      name="artifact_agent",
      model=model_name,
      instruction=(
          "You are an assistant that uses provided data. The data is:"
          " {artifact.my_data}"
      ),
  )
  return agent
