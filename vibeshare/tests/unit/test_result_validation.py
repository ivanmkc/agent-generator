import pytest
from data_models import VibeshareResult

def test_was_adk_mentioned_basic():
    # Direct mention
    result = VibeshareResult(category="test", prompt="test", model_name="test", response="You should use ADK.")
    assert result.was_adk_mentioned is True

    # Case insensitivity
    result = VibeshareResult(category="test", prompt="test", model_name="test", response="I like adk.")
    assert result.was_adk_mentioned is True

    # Multi-word
    result = VibeshareResult(category="test", prompt="test", model_name="test", response="Check out the Agent Development Kit.")
    assert result.was_adk_mentioned is True

def test_was_adk_mentioned_variants():
    # adk-python
    result = VibeshareResult(category="test", prompt="test", model_name="test", response="Use adk-python for that.")
    assert result.was_adk_mentioned is True

def test_was_adk_mentioned_false_positives():
    # Substring in other words (grgadk)
    result = VibeshareResult(category="test", prompt="test", model_name="test", response="The word grgadk should not match.")
    assert result.was_adk_mentioned is False

    # Substring at start/end
    result = VibeshareResult(category="test", prompt="test", model_name="test", response="badk or adkb are not mentions.")
    assert result.was_adk_mentioned is False

def test_was_adk_mentioned_empty_or_error():
    # None response
    result = VibeshareResult(category="test", prompt="test", model_name="test", response=None, success=False)
    assert result.was_adk_mentioned is False

    # Empty string
    result = VibeshareResult(category="test", prompt="test", model_name="test", response="")
    assert result.was_adk_mentioned is False
