"""Test Adk Generator Output module."""

import pytest
import os
import uuid
from benchmarks.answer_generators.adk_agents import create_workflow_adk_generator
from benchmarks.tests.integration.predefined_cases import SIMPLE_API_UNDERSTANDING_CASE
from benchmarks.api_key_manager import ApiKeyManager
from benchmarks.data_models import GeneratedAnswer, ApiUnderstandingAnswerOutput


@pytest.mark.asyncio
async def test_adk_generator_output_structure():
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    # Initialize the generator
    generator = create_workflow_adk_generator(
        model_name="gemini-2.5-flash", api_key_manager=ApiKeyManager()
    )

    try:
        await generator.setup()

        # Generate answer
        run_id = f"test_run_{uuid.uuid4().hex}"
        result: GeneratedAnswer = await generator.generate_answer(
            SIMPLE_API_UNDERSTANDING_CASE, run_id=run_id
        )

        # 1. Verify Output Structure
        assert isinstance(result.output, ApiUnderstandingAnswerOutput)

        # 2. Verify Content
        assert result.output.code, "Generated code should not be empty"
        assert result.output.rationale, "Rationale should not be empty"
        assert (
            "class Event" in result.output.code or "BaseModel" in result.output.code
        ), "Code should contain relevant keywords"

        # 3. Verify Metadata
        assert result.usage_metadata, "Usage metadata should be present"
        assert result.usage_metadata.total_tokens is not None

        # 4. Verify Trace Logs
        assert result.trace_logs, "Trace logs should be present"
        assert len(result.trace_logs) > 0

        # Check for specific log events expected from a workflow agent
        tool_uses = [log for log in result.trace_logs if log.type == "tool_use"]
        # Note: A simple query might not trigger tool use if the model knows the answer,
        # but the system prompt encourages it.
        # For this specific case (JSON output), it might just output text.

        print(f"Generated Code:\n{result.output.code}")
        print(f"Rationale:\n{result.output.rationale}")

    finally:
        await generator.teardown()
