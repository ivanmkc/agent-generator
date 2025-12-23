from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents import SequentialAgent


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates a SequentialAgent that manages inter-agent communication.

    Instructions:
        Create a SequentialAgent named "multi_agent_coordinator" with two sub-agents.
        1. "writer_agent": Outputs "secret_message" to the state key "correct_key".
        2. "reader_agent": Reads from "{correct_key}" and outputs the content.

        Requirements:
        - The `writer_agent` should output 'secret_message'.
        - The `reader_agent` should correctly read and output 'secret_message' from the session state.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        An instance of SequentialAgent with correct multi-agent interaction.
    """
    writer_agent = LlmAgent(
        name="writer_agent",
        model=model_name,
        instruction="Respond with only the text 'secret_message'.",
    )

    reader_agent = LlmAgent(
        name="reader_agent",
        model=model_name,
        instruction=(
            "Your only task is to output the content of '{correct_key}'. Do not"
            " add any other text."
        ),
    )

    root_agent = SequentialAgent(
        name="multi_agent_coordinator",
        sub_agents=[writer_agent, reader_agent],
    )
    return root_agent
