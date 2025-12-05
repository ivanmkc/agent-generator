from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates a root LlmAgent that delegates a task to a specialist sub-agent.

  Instructions:
      Create a "delegator_agent" that delegates to a "specialist_agent" when needed.
      The specialist_agent should be instructed to respond with "specialist ok".

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of LlmAgent capable of delegation.
  """
  specialist_agent = LlmAgent(
      name="specialist_agent",
      model=model_name,
      instruction=(
          "You are a specialist. You only respond with 'specialist ok'."
      ),
      description="Use this agent for specialist tasks.",
  )

  root_agent = LlmAgent(
      name="delegator_agent",
      model=model_name,
      sub_agents=[specialist_agent],
      instruction=(
          "You are a delegator. If the user asks for a specialist, delegate the"
          " task to the 'specialist_agent'."
      ),
  )
  return root_agent
