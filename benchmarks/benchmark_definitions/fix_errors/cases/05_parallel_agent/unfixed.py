from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents import ParallelAgent


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates a ParallelAgent that runs two LlmAgents concurrently.

    Instructions:
        Create a ParallelAgent named "parallel_coordinator" with two sub-agents:
        1. "agent_one": Responds with "This is the first parallel agent."
        2. "agent_two": Responds with "This is the second parallel agent."

        Requirements:
        - The final response should contain the word 'parallel'.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        An instance of ParallelAgent with configured sub-agents.
    """
    raise NotImplementedError("Agent implementation incomplete.")
