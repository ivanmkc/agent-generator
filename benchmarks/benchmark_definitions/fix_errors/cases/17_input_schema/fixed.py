from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from pydantic import BaseModel
from pydantic import Field


class UserInfo(BaseModel):
  name: str = Field(description="The user's name.")
  age: int = Field(description="The user's age.")


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates an LlmAgent that uses `input_schema` for structured input.

  Instructions:
      Create a "worker" agent that accepts user info (name: str, age: int) via `input_schema`.
      Then, create a root "agent" that uses the worker as a tool to process user info.

      Requirements:
      - The worker agent should be initialized with an `input_schema` of `UserInfo`.
      - The worker agent should be able to process a JSON string conforming to the `UserInfo` schema.
      - The worker agent's response should include the user's name and age from the input.
      - The worker agent's name should be "worker".

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of LlmAgent with a configured input schema.
  """
  worker_agent = LlmAgent(
      name="worker",
      model=model_name,
      instruction="Acknowledge the user's name and age.",
      input_schema=UserInfo,
  )
  agent = LlmAgent(
      name="agent",
      model=model_name,
      tools=[AgentTool(agent=worker_agent)],
      instruction="Use the worker agent to process the user's info.",
  )
  return agent
