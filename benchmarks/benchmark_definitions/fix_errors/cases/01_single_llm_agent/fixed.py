from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates a minimal LlmAgent.

    Instructions:
        Create a helpful LlmAgent named "single_agent" that responds to greetings.

        Requirements:
        - The agent should respond to the greeting 'Hello' with a response containing 'Hello'.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        An instance of LlmAgent.
    """
    root_agent = LlmAgent(
        name="single_agent",
        model=model_name,
        instruction="You are a helpful assistant.",
    )
    return root_agent
