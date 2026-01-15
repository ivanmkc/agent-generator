from __future__ import annotations

from google.adk.agents import BaseAgent, LlmAgent


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates a minimal LlmAgent.

  Instructions:
      Create an LlmAgent named "my_valid_agent" that responds to greetings.

      Requirements:
      - The agent should be named 'my_valid_agent'.
      - The agent should use the provided `model_name`.
      - The agent should respond to 'Hello' with a response containing 'Hello'.

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of LlmAgent.
  """
  return LlmAgent(
      name="my agent",
      model=model_name,
      instruction="You are a helpful assistant.",
  )
