from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates an LlmAgent that uses an OpenAI model via LiteLlm.

    Instructions:
        Create an LlmAgent named "openai_agent" that uses the `LiteLlm` model wrapper.
        The LiteLlm should be configured with `model="openai/gpt-3.5-turbo"`.

        Requirements:
        - The agent should be able to respond to a greeting.
        - The final response should contain the word 'Hello'.

    Args:
        model_name: The name of the LLM model to use (for consistency, not directly used in LiteLlm here).

    Returns:
        An instance of LlmAgent configured with LiteLlm for OpenAI.
    """
    raise NotImplementedError("Agent implementation incomplete.")
