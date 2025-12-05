from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool


def basic_tool(query: str) -> str:
  """A simple tool that returns a fixed string."""
  return f"The tool received the query: {query}"


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates an LlmAgent configured with a basic function tool.

  Instructions:
      Create an LlmAgent named "tool_agent" equipped with the `basic_tool`.
      The agent should be able to use the tool when prompted.

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of LlmAgent with a configured tool.
  """
  root_agent = LlmAgent(
      name="tool_agent",
      model=model_name,
      instruction="Use the `basic_tool` with the query 'test'.",
      tools=[FunctionTool(func=basic_tool)],
  )
  return root_agent
