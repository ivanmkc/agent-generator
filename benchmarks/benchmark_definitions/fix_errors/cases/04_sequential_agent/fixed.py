from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents import SequentialAgent


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates a SequentialAgent that orchestrates two simple LlmAgents.

    Instructions:
        Create a SequentialAgent named "sequential_coordinator" with two sub-agents:
        1. "agent_one": Responds with "one".
        2. "agent_two": Responds with "two".

        Requirements:
        - The final response should come from the second agent, containing the word 'two'.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        An instance of SequentialAgent with configured sub-agents.
    """
    agent_one = LlmAgent(
        name="agent_one",
        model=model_name,
        instruction="This is the first agent. Respond with 'one'.",
    )
    agent_two = LlmAgent(
        name="agent_two",
        model=model_name,
        instruction="This is the second agent. Respond with 'two'.",
    )

    root_agent = SequentialAgent(
        name="sequential_coordinator", sub_agents=[agent_one, agent_two]
    )
    return root_agent
