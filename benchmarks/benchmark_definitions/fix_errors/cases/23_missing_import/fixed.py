from __future__ import annotations

from google.adk.agents import LlmAgent


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates an LlmAgent with the necessary import statement.

    Instructions:
        Create an LlmAgent named "import_agent".
        Ensure all necessary modules (like LlmAgent) are imported.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        An instance of LlmAgent.
    """
    from google.adk.agents import LlmAgent

    root_agent = LlmAgent(
        name="import_agent",
        model=model_name,
        instruction="You are a helpful assistant.",
    )
    return root_agent
