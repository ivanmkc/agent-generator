"""
Benchmark Case 12: An App instance that includes a basic plugin.

Description:
  This benchmark tests the ability to create an `App` instance named 'app'
  that includes a custom plugin (`SimplePlugin`) and a root agent.

Test Verification:
  - Verifies that `create_agent` returns a valid App instance that:
    - Has a root agent.
    - Includes the `SimplePlugin`.
    - Can execute the root agent to return a greeting ("Hello").
"""

import pytest

from benchmarks.test_helpers import MODEL_NAME
from benchmarks.test_helpers import run_agent_test


def test_create_agent_unfixed_fails():
    import unfixed

    with pytest.raises(NotImplementedError, match="Agent implementation incomplete."):
        unfixed.create_agent(MODEL_NAME)


@pytest.mark.asyncio
async def test_create_agent_passes():
    import fixed

    app = fixed.create_agent(MODEL_NAME)
    response = await run_agent_test(app.root_agent, "Hello", mock_llm_response="Hello")
    assert "Hello" in response

    from google.adk.apps import App

    assert isinstance(app, App), "Returned object should be an App instance."
    assert app.name == "my_app", "App name mismatch."
    assert len(app.plugins) > 0, "App should have plugins."
    assert app.plugins[0].name == "simple_plugin", "Plugin name mismatch."
    assert app.root_agent.name == "app_agent", "Root agent name mismatch."
