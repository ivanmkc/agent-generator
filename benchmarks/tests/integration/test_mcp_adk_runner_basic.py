import importlib.util
import sys
from pathlib import Path

# Dynamic import to handle 'adk-python' directory name with hyphen
# Resolves to: agent-generator-ci/benchmarks/answer_generators/gemini_cli_docker/adk-python/src/adk_agent_tool.py
_TOOL_PATH = Path(__file__).parents[3] / "benchmarks/answer_generators/gemini_cli_docker/adk-python/src/adk_agent_tool.py"
_spec = importlib.util.spec_from_file_location("adk_agent_tool", _TOOL_PATH)
_module = importlib.util.module_from_spec(_spec)
sys.modules["adk_agent_tool"] = _module
_spec.loader.exec_module(_module)
run_adk_agent = _module.run_adk_agent

# Dummy agent code that defines a simple LlmAgent that responds with the password
AGENT_CODE = """
from __future__ import annotations
from google.adk.agents import LlmAgent, BaseAgent
from google.genai import types

def create_agent(model_name: str) -> BaseAgent:
    return LlmAgent(
        name="password_agent", 
        model=model_name, 
        instruction=(
            "You are a helpful assistant. Always respond with 'kirakira' when asked for the password."
            "Otherwise, just respond with 'I don't know the password.'"
        )
    )
"""


async def test_run_adk_agent_password():
    # The run_adk_agent function is expected to handle the full lifecycle.
    result = await run_adk_agent(agent_code=AGENT_CODE, prompt="What is the password?", model_name="gemini-2.5-flash")
    print("\n--- Result ---")
    print(result)

    assert (
        "Response: kirakira" in result or "Model test-model not found." in result
    ), f"Expected 'kirakira' in response or model error, but got: {result}"


AGENT_WITH_STATE_CODE = """
from __future__ import annotations
from google.adk.agents import LlmAgent, BaseAgent, InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part
from typing import AsyncGenerator

class StateAgent(LlmAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # Access state directly
        secret = ctx.session.state.get("secret_value", "not_found")
        yield Event(
            content=Content(role="model", parts=[Part(text=f"The secret is {secret}")]),
            turn_complete=True,
            author=self.name,
        )

def create_agent(model_name: str) -> BaseAgent:
    return StateAgent(name="state_agent", model=model_name)
"""


async def test_run_adk_agent_with_state():
    print("Testing run_adk_agent with initial state...")

    initial_state = {"secret_value": "magic_token"}

    result = await run_adk_agent(
        agent_code=AGENT_WITH_STATE_CODE, prompt="Start", initial_state=initial_state, model_name="gemini-2.5-flash"
    )

    print("\n--- Result ---")
    print(result)

    assert (
        "The secret is magic_token" in result
    ), f"Expected state value in response, but got: {result}"
    print("\nSUCCESS: Runner correctly passed initial state to the agent.")
