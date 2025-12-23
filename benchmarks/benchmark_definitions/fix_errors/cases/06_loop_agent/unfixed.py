from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents import LoopAgent


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates a LoopAgent that runs a sub-agent a fixed number of times.

    Instructions:
        Create a LoopAgent named "loop_coordinator" that runs a sub-agent named
        "looper_agent" for 2 iterations.

        Requirements:
        - The final response should contain the word 'loop'.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        An instance of LoopAgent with configured sub-agents and iterations.
    """
    raise NotImplementedError("Agent implementation incomplete.")
