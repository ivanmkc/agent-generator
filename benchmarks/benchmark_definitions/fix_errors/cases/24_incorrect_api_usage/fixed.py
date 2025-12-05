from __future__ import annotations

from google.adk.agents import LlmAgent


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates an LlmAgent.

  Instructions:
      Create an LlmAgent named "api_agent".
      Ensure that you use the correct arguments for the LlmAgent constructor
      (e.g., `instruction` vs `instructions`).

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of LlmAgent.
  """
  root_agent = LlmAgent(
      name="api_agent",
      model=model_name,
      instruction="You are a helpful assistant.",
  )
  return root_agent
