from __future__ import annotations

from typing import Optional

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse


def my_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
  """
  A callback that modifies the response content.

  Instructions:
      Implement this callback to append the string " (modified by callback)"
      to the text of the first part of the response content.
  """
  # TODO: Implement the callback logic here.
  pass


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
  raise NotImplementedError("Agent implementation incomplete.")
