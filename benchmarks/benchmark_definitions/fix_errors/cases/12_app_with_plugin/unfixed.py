from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.plugins import BasePlugin


class SimplePlugin(BasePlugin):
  """A simple plugin that adds a prefix to the response."""

  def __init__(self) -> None:
    super().__init__(name="simple_plugin")

  async def after_agent_callback(self, **kwargs) -> None:
    # This is a simplified example. A real plugin would modify the event.
    print("SimplePlugin: after_agent_callback")


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates an App instance that includes a basic plugin and a root LlmAgent.

  Instructions:
      Create an App named "my_app" with a root agent named "app_agent".
      The app must include the provided `SimplePlugin`.
      The root agent should respond to greetings.

      Requirements:
      - The app must define a plugin that inherits from `BasePlugin`.
      - The final response should contain the word 'Hello'.

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of App with a configured plugin.
  """
  raise NotImplementedError("Agent implementation incomplete.")
