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
        Ensure the producer sets the correct output key so the consumer can read it.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        An instance of SequentialAgent with correct multi-agent interaction.
    """
    MODEL_NAME = model_name  # Local variable for the snippet

    writer_agent = LlmAgent(
        name="writer_agent",
        model=MODEL_NAME,
        instruction="Respond with only the text 'secret_message'.",
        output_key="correct_key",
    )

    reader_agent = LlmAgent(
        name="reader_agent",
        model=MODEL_NAME,
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
