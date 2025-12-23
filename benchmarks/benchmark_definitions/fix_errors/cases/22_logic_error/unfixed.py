from __future__ import annotations

from google.adk.agents import BaseAgent, LlmAgent


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates a LogicAgent that responds with "Hello World!".

    Instructions:
        Create a LogicAgent named "logic_agent".

        Requirements:
        - The agent should respond to the greeting 'Say hello.' with 'Hello World!'.
        - For any other input, the agent should respond with 'Goodbye!'.
        - The agent MUST NOT use an LLM for generation (it must use deterministic logic).

    Args:
        model_name: The name of the LLM model to use (ignored).

    Returns:
        An instance of LogicAgent with the correct logic.
    """
    raise NotImplementedError("Implement the LogicAgent here.")
