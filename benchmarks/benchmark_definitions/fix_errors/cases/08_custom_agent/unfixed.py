from __future__ import annotations

from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event


class CustomConditionalAgent(BaseAgent):
    """A custom agent that runs one of two sub-agents based on session state."""

    agent_a: LlmAgent
    agent_b: LlmAgent

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        should_run_a = ctx.session.state.get("run_agent_a", False)

        if should_run_a:
            async for event in self.agent_a.run_async(ctx):
                yield event
        else:
            async for event in self.agent_b.run_async(ctx):
                yield event


def create_agent(model_name: str) -> BaseAgent:
    """
    Creates a custom agent with conditional logic based on session state.

    Instructions:
        Create a CustomConditionalAgent named "custom_conditional_agent".
        It should run "agent_a" if session.state["run_agent_a"] is True, otherwise "agent_b".
        - "agent_a" should respond "Agent A was chosen."
        - "agent_b" should respond "Agent B was chosen."

        Requirements:
        - If `run_agent_a` is true, the final response should contain 'Agent A'.
        - If `run_agent_a` is false, the final response should contain 'Agent B'.

    Args:
        model_name: The name of the LLM model to use.

    Returns:
        An instance of CustomConditionalAgent.
    """
    raise NotImplementedError("Agent implementation incomplete.")
