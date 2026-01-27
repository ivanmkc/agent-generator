"""Test Cli Json Extraction module."""

import pytest
from benchmarks.answer_generators.gemini_cli_answer_generator import GeminiCliAnswerGenerator
from unittest.mock import MagicMock


def test_extract_json_from_text_with_markdown():
    """Tests extraction from standard markdown code blocks."""
    text = 'Here is the result:\n```json\n{"answer": 42}\n```\nHope this helps!'
    # We can use a mock for the abstract parts since we only test the helper method
    generator = MagicMock(spec=GeminiCliAnswerGenerator)
    # Re-bind the real method to the mock for testing
    generator._extract_json_from_text = (
        GeminiCliAnswerGenerator._extract_json_from_text.__get__(generator)
    )

    result = generator._extract_json_from_text(text)
    assert result == '{"answer": 42}'


def test_extract_json_from_text_conversational():
    """Tests extraction from conversational text without code blocks."""
    text = 'The correct configuration is {"key": "value"} which I found in the docs.'
    generator = MagicMock(spec=GeminiCliAnswerGenerator)
    generator._extract_json_from_text = (
        GeminiCliAnswerGenerator._extract_json_from_text.__get__(generator)
    )

    result = generator._extract_json_from_text(text)
    assert result == '{"key": "value"}'


def test_extract_json_from_text_nested_braces():
    """Tests extraction when there are multiple sets of braces (should pick outermost)."""
    text = 'Check this: {"outer": {"inner": 1}} and that\'s it.'
    generator = MagicMock(spec=GeminiCliAnswerGenerator)
    generator._extract_json_from_text = (
        GeminiCliAnswerGenerator._extract_json_from_text.__get__(generator)
    )

    result = generator._extract_json_from_text(text)
    assert result == '{"outer": {"inner": 1}}'


def test_extract_json_from_text_raw():
    """Tests that raw JSON is returned as-is."""
    text = '{"raw": true}'
    generator = MagicMock(spec=GeminiCliAnswerGenerator)
    generator._extract_json_from_text = (
        GeminiCliAnswerGenerator._extract_json_from_text.__get__(generator)
    )

    result = generator._extract_json_from_text(text)
    assert result == '{"raw": true}'


def test_extract_json_from_text_no_json():
    """Tests fallback when no JSON is found."""
    text = "Just some text with no braces."
    generator = MagicMock(spec=GeminiCliAnswerGenerator)
    generator._extract_json_from_text = (
        GeminiCliAnswerGenerator._extract_json_from_text.__get__(generator)
    )

    result = generator._extract_json_from_text(text)
    assert result == text
