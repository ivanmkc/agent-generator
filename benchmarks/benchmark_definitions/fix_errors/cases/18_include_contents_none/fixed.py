from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates a stateless LlmAgent using `include_contents="none"`.

    Instructions:
        Create an LlmAgent named "StatelessBot" that is stateless.
        It should not retain conversation history (set `include_contents="none"`).

        Requirements:
        - The agent's name should be 'StatelessBot'.
        - The agent should be initialized with `include_contents='none'`.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        A stateless instance of LlmAgent.
    """
    agent = LlmAgent(
        name="StatelessBot",
        model=model_name,
        instruction=(
            "Your name is StatelessBot. You are a stateless agent and do not"
            " retain information from previous turns."
        ),
        include_contents="none",
    )
    return agent
