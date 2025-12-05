from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.code_executors.built_in_code_executor import BuiltInCodeExecutor


def create_agent(model_name: str) -> BaseAgent:
  """
  Creates an LlmAgent configured with a BuiltInCodeExecutor.

  Instructions:
      Create an LlmAgent named "code_exec_agent" equipped with a `BuiltInCodeExecutor`.
      The agent should be instructed to use the code executor to calculate "2 + 2".

  Args:
      model_name: The name of the LLM model to use.

  Returns:
      An instance of LlmAgent with a configured code executor.
  """
  root_agent = LlmAgent(
      name="code_exec_agent",
      model=model_name,
      instruction=(
          "You are a helpful assistant. Use the code executor to calculate 2"
          " + 2."
      ),
      code_executor=BuiltInCodeExecutor(),
  )
  return root_agent
