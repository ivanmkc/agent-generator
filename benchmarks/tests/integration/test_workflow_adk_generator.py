import pytest
import os
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.tests.integration.predefined_cases import SIMPLE_API_UNDERSTANDING_CASE
from benchmarks.api_key_manager import ApiKeyManager

@pytest.mark.asyncio
async def test_workflow_adk_generator_api_understanding():
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    # Initialize the generator
    # We rely on the default workspace creation (temp dir)
    generator = AdkAnswerGenerator(
        model_name="gemini-2.5-flash",
        api_key_manager=ApiKeyManager(),
        enable_workflow=True
    )

    try:
        print(f"--- [Setup] Initializing {generator.name} ---")
        await generator.setup()

        print(f"--- [Run] Generating answer for: {SIMPLE_API_UNDERSTANDING_CASE.question} ---")
        result = await generator.generate_answer(SIMPLE_API_UNDERSTANDING_CASE)

        print(f"--- [Result] Answer: {result.output.code}")
        
        # Basic validation that it produced something reasonable
        assert result.output.code
        assert "class Event" in result.output.code or "BaseModel" in result.output.code

    finally:
        await generator.teardown()
