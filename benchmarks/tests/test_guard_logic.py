import pytest
import asyncio
from google.adk.agents import Agent, LlmAgent, SequentialAgent, InvocationContext
from google.adk.runners import InMemoryRunner
from google.adk.apps import App
from google.genai import types

from google.adk.events import Event

# --- Mocks & Stubs ---

class FailingSetupAgent(Agent):
    """Simulates an agent that fails to produce the expected output."""
    output_key: str = ""

    def __init__(self, output_key: str):
        super().__init__(name="failing_setup", output_key=output_key)

    async def _run_async_impl(self, ctx: InvocationContext):
        # Simulate failure by NOT setting the state key, or setting it to None
        ctx.session.state[self.output_key] = None
        yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Setup failed (simulated).")]))

class NaiveSolverAgent(Agent):
    """Simulates a solver that runs blindly."""
    input_key: str = ""
    was_run: bool = False
    received_input: str | None = None

    def __init__(self, input_key: str):
        super().__init__(name="naive_solver", input_key=input_key)

    async def _run_async_impl(self, ctx: InvocationContext):
        self.was_run = True
        self.received_input = ctx.session.state.get(self.input_key)
        # Simulate hallucination/garbage output when input is None
        if self.received_input is None:
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="# Error: No code found.")]))
        else:
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Code generated successfully.")]))

# --- Guard Implementation ---

from google.adk.agents import Agent, LlmAgent, SequentialAgent, InvocationContext
from google.adk.agents.callback_context import CallbackContext

# ...

def input_guard_callback(callback_context: CallbackContext):
    """
    Guard callback to validate inputs before the agent runs.
    Raises ValueError if required inputs are missing.
    """
    try:
        # Try to guess the attribute name based on common ADK patterns
        if hasattr(callback_context, 'invocation_context'):
            ctx = callback_context.invocation_context
        elif hasattr(callback_context, 'context'):
            ctx = callback_context.context
        elif hasattr(callback_context, '_invocation_context'):
            ctx = callback_context._invocation_context
        else:
            raise AttributeError(f"CallbackContext attributes: {dir(callback_context)}")
    except Exception as e:
        raise e

    req = ctx.session.state.get("sanitized_request")
    if req is None or req == "null":
        raise ValueError(f"GUARD: Input 'sanitized_request' is null/missing. Aborting.")
    if req is None or req == "null":
        # We can't easily access agent.name here unless we bind it, but the error message is enough.
        raise ValueError(f"GUARD: Input 'sanitized_request' is null/missing. Aborting.")

# --- Tests ---

@pytest.mark.asyncio
async def test_cascade_failure_without_guard():
    """Verifies that without a guard, the solver runs with None input."""
    
    setup = FailingSetupAgent(output_key="sanitized_request")
    solver = NaiveSolverAgent(input_key="sanitized_request")
    
    chain = SequentialAgent(name="chain", sub_agents=[setup, solver])
    app = App(name="test_app", root_agent=chain)
    runner = InMemoryRunner(app=app)
    session = await runner.session_service.create_session(app_name="test_app", user_id="test_user")

    # Run
    async for _ in runner.run_async(session_id=session.id, user_id=session.user_id, new_message=types.Content(parts=[types.Part(text="start")])):
        pass

    # Assertions
    assert solver.was_run is True
    assert solver.received_input is None
    # This confirms the "Cascade Failure": Solver ran despite bad input.

@pytest.mark.asyncio
async def test_guard_prevents_cascade():
    """Verifies that the guard callback prevents the solver from running."""
    
    setup = FailingSetupAgent(output_key="sanitized_request")
    solver = NaiveSolverAgent(input_key="sanitized_request")
    
    # Attach Guard
    solver.before_agent_callback = input_guard_callback
    
    chain = SequentialAgent(name="chain", sub_agents=[setup, solver])
    app = App(name="test_app", root_agent=chain)
    runner = InMemoryRunner(app=app)
    session = await runner.session_service.create_session(app_name="test_app", user_id="test_user")

    # Run and expect error
    with pytest.raises(ValueError, match="GUARD: Input 'sanitized_request' is null"):
        async for _ in runner.run_async(session_id=session.id, user_id=session.user_id, new_message=types.Content(parts=[types.Part(text="start")])):
            pass

    # Assertions
    # In ADK, if before_agent_callback raises, the agent's body (_run_async_impl) should NOT run.
    assert solver.was_run is False
