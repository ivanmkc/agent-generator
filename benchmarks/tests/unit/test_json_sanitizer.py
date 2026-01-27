"""Test Json Sanitizer module."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from pydantic import BaseModel
from benchmarks.parsing.json_sanitizer import JsonSanitizer


class SimpleSchema(BaseModel):
    name: str
    age: int


@pytest.mark.asyncio
async def test_sanitize_direct_valid():
    s = JsonSanitizer()
    text = '{"name": "Alice", "age": 30}'
    result = await s.sanitize(text, SimpleSchema)
    assert result.name == "Alice"


@pytest.mark.asyncio
async def test_sanitize_regex_code_block():
    s = JsonSanitizer()
    text = 'Here is the json:\n```json\n{"name": "Bob", "age": 40}\n```'
    result = await s.sanitize(text, SimpleSchema)
    assert result.name == "Bob"


@pytest.mark.asyncio
async def test_sanitize_llm_fallback(monkeypatch):
    mock_api = MagicMock()
    mock_api.get_next_key = AsyncMock(return_value="fake_key")

    # Mock Client
    mock_client_cls = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_cls.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.text = '{"name": "Charlie", "age": 50}'

    mock_client_instance.aio.models.generate_content = AsyncMock(
        return_value=mock_response
    )

    monkeypatch.setattr("benchmarks.parsing.json_sanitizer.Client", mock_client_cls)

    s = JsonSanitizer(api_key_manager=mock_api)
    text = "My name is Charlie and I am 50 years old."  # Unstructured

    result = await s.sanitize(text, SimpleSchema)
    assert result.name == "Charlie"

    # Verify LLM was called
    mock_client_instance.aio.models.generate_content.assert_called_once()
