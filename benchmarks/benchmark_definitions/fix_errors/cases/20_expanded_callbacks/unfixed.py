from __future__ import annotations

from google.adk.agents import BaseAgent


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates an LlmAgent with `before_tool_callback` and `after_tool_callback`.

  Instructions:
      Create an LlmAgent named "callback_agent" with the `_mock_tool_func`.
      Register `before_callback_func` and `after_callback_func` as the before/after tool callbacks.

      Requirements:
      - The agent should use `before_callback_func` as its `before_tool_callback`.
      - The agent should use `after_callback_func` as its `after_tool_callback`.
      - The final response should contain 'UNIQUE_TOOL_OUTPUT_FOR_TEST: hello'.

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of LlmAgent with configured tool callbacks.
  """
  raise NotImplementedError("Agent implementation incomplete.")
