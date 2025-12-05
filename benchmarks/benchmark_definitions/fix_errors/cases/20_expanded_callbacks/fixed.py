from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse
from google.adk.tools import BaseTool
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext


async def _mock_tool_func(query: str) -> str:
  return f"UNIQUE_TOOL_OUTPUT_FOR_TEST: {query}"


class CallbackTracker:
  """A class to track callback execution for testing purposes."""

  def __init__(self):
    self.before_logs: List[bool] = []
    self.after_logs: List[bool] = []

  async def before_tool_callback(
      self, tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
  ) -> Optional[Dict[str, Any]]:
    """Callback executed before a tool call."""
    self.before_logs.append(True)
    return None

  async def after_tool_callback(
      self,
      tool: BaseTool,
      args: Dict[str, Any],
      tool_context: ToolContext,
      tool_response: Dict[str, Any],
  ) -> Optional[Dict[str, Any]]:
    """Callback executed after a tool call."""
    self.after_logs.append(True)
    return None


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates an LlmAgent with `before_tool_callback` and `after_tool_callback`.

  Instructions:
      Create an LlmAgent named "callback_agent" with the `_mock_tool_func`.
      Register `before_callback_func` and `after_callback_func` as the before/after tool callbacks.

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of LlmAgent with configured tool callbacks.
  """
  tracker = CallbackTracker()

  root_agent = LlmAgent(
      name="callback_agent",
      model=model_name,
      instruction=(
          "Use the test_tool to respond to the user. Return the tool's output"
          " verbatim."
      ),
      tools=[FunctionTool(func=_mock_tool_func)],
      before_tool_callback=tracker.before_tool_callback,
      after_tool_callback=tracker.after_tool_callback,
  )
  # Attach the tracker instance directly to the agent for test verification.
  # This is for testing purposes only, not standard ADK practice.
  setattr(root_agent, "_test_tracker", tracker)

  return root_agent
