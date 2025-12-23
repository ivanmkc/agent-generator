from __future__ import annotations

from typing import Optional

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse


def my_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """A callback that modifies the response content."""
    if (
        llm_response.content
        and llm_response.content.parts
        and llm_response.content.parts[0].text
    ):
        llm_response.content.parts[0].text += " (modified by callback)"
    return llm_response


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates an LlmAgent with an `after_model_callback` configured.

    Instructions:
        Create an LlmAgent named "callback_agent" that registers the `my_callback` function
        as its `after_model_callback`.

        Requirements:
        - The agent should use the `my_callback` function as its `after_model_callback`.
        - When the agent responds, the text " (modified by callback)" should be appended to the output.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        An instance of LlmAgent with a configured after-model callback.
    """
    root_agent = LlmAgent(
        name="callback_agent",
        model=model_name,
        instruction="You are a helpful assistant.",
        after_model_callback=my_callback,
    )
    return root_agent
