from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents import SequentialAgent


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates a SequentialAgent that demonstrates inter-agent state management.

    Instructions:
        Create a SequentialAgent named "state_management_coordinator" with two sub-agents:
        1. "writer_agent": Writes the value 'xyz' to the session state key "secret_word".
        2. "reader_agent": Reads the value from "secret_word" and outputs it.

        Requirements:
        - The 'writer' agent should write the value 'xyz' to a key named 'secret_word' in the session state.
        - The 'reader' agent should read the value from 'secret_word' and the final response must contain 'xyz'.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        An instance of SequentialAgent with state-managing sub-agents.
    """
    raise NotImplementedError("Agent implementation incomplete.")
