from __future__ import annotations

from typing import Optional

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.plugins import BasePlugin
from google.genai import types


class SimplePlugin(BasePlugin):
    """A simple plugin that adds a prefix to the response."""

    def __init__(self) -> None:
        super().__init__(name="simple_plugin")

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        # This is a simplified example. A real plugin would modify the event.
        print(f"SimplePlugin: after_agent_callback for {agent.name}")
        return None


def create_agent(model_name: str) -> App:
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
    root_agent = LlmAgent(
        name="app_agent",
        model=model_name,
        instruction="You are an agent within an App.",
    )

    app = App(
        name="my_app",
        root_agent=root_agent,
        plugins=[SimplePlugin()],
    )
    return app
