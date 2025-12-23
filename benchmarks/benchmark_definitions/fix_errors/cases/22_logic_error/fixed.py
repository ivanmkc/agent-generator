from __future__ import annotations

from typing import AsyncGenerator

from google.adk.agents import BaseAgent, InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part


class LogicAgent(BaseAgent):

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        user_text = ""
        if ctx.user_content and ctx.user_content.parts:
            for part in ctx.user_content.parts:
                if part.text:
                    user_text += part.text

        if "Say hello." in user_text:
            response_text = "Hello World!"
        else:
            response_text = "Goodbye!"

        yield Event(
            content=Content(role="model", parts=[Part(text=response_text)]),
            turn_complete=True,
            author=self.name,
        )


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates a LogicAgent that responds with "Hello World!".

    Instructions:
        Create a LogicAgent named "logic_agent".

    Args:
        model_name: The name of the LLM model to use (ignored).

    Returns:
        An instance of LogicAgent with the correct logic.
    """
    root_agent = LogicAgent(name="logic_agent")
    return root_agent
