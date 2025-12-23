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
    raise NotImplementedError("Agent implementation incomplete.")
