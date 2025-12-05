from __future__ import annotations

from typing import Any
from typing import Dict
from typing import Optional

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.tools import BaseTool
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext


async def mock_tool_func(query: str) -> Dict[str, str]:
  return {"output": f"Tool Output: {query}"}


async def before_callback_func(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext
) -> Optional[Dict[str, Any]]:
  """Callback executed before a tool call."""
  if "query" in args and isinstance(args["query"], str):
    args["query"] = args["query"].upper()
  return None


async def after_callback_func(
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext,
    tool_response: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
  """Callback executed after a tool call."""
  if isinstance(tool_response, dict) and "output" in tool_response:
    tool_response["output"] += " [Verified]"
    return tool_response
  return None


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates an LlmAgent with `before_tool_callback` and `after_tool_callback`.

  Instructions:
      Create an LlmAgent named "callback_agent" with the `mock_tool_func`.
      Register `before_callback_func` and `after_callback_func` as the before/after tool callbacks.

      Requirements:
      - `before_callback_func` MUST uppercase the 'query' argument.
      - `after_callback_func` MUST append ' [Verified]' to the tool output.

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of LlmAgent with configured tool callbacks.
  """
  root_agent = LlmAgent(
      name="callback_agent",
      model=model_name,
      instruction=(
          "Use the mock_tool_func to respond to the user. Return the tool's output"
          " verbatim."
      ),
      tools=[FunctionTool(func=mock_tool_func)],
      before_tool_callback=before_callback_func,
      after_tool_callback=after_callback_func,
  )
  return root_agent
