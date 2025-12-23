"""
Benchmark Case 20: Build integrity test for LlmAgent with expanded callbacks.

Description:
  This benchmark tests the ability to create an `LlmAgent` with `before_tool_callback`
  and `after_tool_callback` hooks.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Executes the tool.
    - Triggers the `before_tool_callback`.
    - Triggers the `after_tool_callback`.
    - Returns the tool's output.
"""

from unittest.mock import patch

from google.adk.apps import App
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types
import pytest

from benchmarks.test_helpers import MODEL_NAME


def test_create_agent_unfixed_fails():
    import unfixed

    with pytest.raises(NotImplementedError, match="Agent implementation incomplete."):
        unfixed.create_agent(MODEL_NAME)


@pytest.mark.asyncio
async def test_create_agent_passes():
    import fixed

    root_agent = fixed.create_agent(MODEL_NAME)

    # Manually run the agent logic with mocks
    with patch(
        "google.adk.models.google_llm.Gemini.generate_content_async"
    ) as mock_generate:

        async def async_response_gen_tool_call():
            response = types.GenerateContentResponse()
            response.candidates = [
                types.Candidate(
                    content=types.Content(
                        parts=[
                            types.Part(
                                function_call=types.FunctionCall(
                                    name="mock_tool_func", args={"query": "hello"}
                                )
                            )
                        ],
                        role="model",
                    )
                )
            ]
            yield LlmResponse.create(response)

        async def async_response_gen_final():
            response = types.GenerateContentResponse()
            response.candidates = [
                types.Candidate(
                    finish_reason="STOP",
                    content=types.Content(
                        parts=[types.Part(text="UNIQUE_TOOL_OUTPUT_FOR_TEST: hello")],
                        role="model",
                    ),
                )
            ]
            yield LlmResponse.create(response)

        response_iter = iter(
            [async_response_gen_tool_call(), async_response_gen_final()]
        )
        mock_generate.side_effect = lambda *args, **kwargs: next(response_iter)

        app = App(name=f"test_app_{root_agent.name}", root_agent=root_agent)
        runner = InMemoryRunner(app=app)

        session = await runner.session_service.create_session(
            app_name=app.name, user_id="test-user", state={}
        )

        tool_output_found = False
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(
                role="user", parts=[types.Part(text="Use the tool with 'hello'")]
            ),
        ):
            function_responses = event.get_function_responses()
            if function_responses:
                for resp in function_responses:
                    # Verify the mutation happened:
                    # 1. Argument 'hello' -> 'HELLO' (visible in output text)
                    # 2. Suffix ' [Verified]' added
                    if (
                        resp.response
                        and "output" in resp.response
                        and "Tool Output: HELLO [Verified]" in resp.response["output"]
                    ):
                        tool_output_found = True

        assert tool_output_found, "Did not find expected mutated tool output."
        assert (
            root_agent.before_tool_callback is not None
        ), "before_tool_callback missing."
        assert (
            root_agent.after_tool_callback is not None
        ), "after_tool_callback missing."
        assert root_agent.name == "callback_agent", "Agent name mismatch."
