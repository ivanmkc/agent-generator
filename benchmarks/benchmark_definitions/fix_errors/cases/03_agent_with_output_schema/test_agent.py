"""
Benchmark Case 03: An LlmAgent that uses output_schema to enforce JSON output.

Description:
  This benchmark tests the ability to create an LlmAgent that uses an `output_schema`
  to produce structured JSON output.

Test Verification:
  - Verifies that `create_agent` returns a valid LlmAgent that:
    - Uses the `BasicOutputSchema` (or equivalent).
    - Produces a valid JSON string when prompted.
    - The JSON contains keys 'field_one' and 'field_two'.
"""

import json

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

    root_agent = fixed.create_agent(MODEL_NAME)
    response = await run_agent_test(
        root_agent,
        "Output JSON",
        mock_llm_response='{"field_one": "value1", "field_two": 2}',
    )

    try:
        data = json.loads(response)
        assert "field_one" in data
        assert "field_two" in data
    except json.JSONDecodeError:
        pytest.fail("The response was not valid JSON.")

    assert root_agent.output_schema is not None, "Agent should have an output_schema."

    # Verify schema fields
    schema_fields = root_agent.output_schema.model_fields
    assert "field_one" in schema_fields
    assert "field_two" in schema_fields
