from __future__ import annotations

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from pydantic import BaseModel
from pydantic import Field


class BasicOutputSchema(BaseModel):
    field_one: str = Field(description="The first field.")
    field_two: int = Field(description="The second field.")


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates an LlmAgent that enforces JSON output using `output_schema`.

    Instructions:
        Create an LlmAgent named "output_schema_agent" that uses `BasicOutputSchema`
        to enforce structured JSON output.

        Requirements:
        - The agent's output must be a valid JSON string.
        - The JSON output must contain the keys 'field_one' and 'field_two'.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        An instance of LlmAgent with a configured output schema.
    """
    root_agent = LlmAgent(
        name="output_schema_agent",
        model=model_name,
        instruction=(
            "Output a JSON object with two fields: 'field_one' and 'field_two'."
        ),
        output_schema=BasicOutputSchema,
    )
    return root_agent
