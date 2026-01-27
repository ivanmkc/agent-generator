"""Test Framework Detection module."""

import pytest
from data_models import VibeshareResult


class TestFrameworkDetection:

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("This uses the ADK for development.", True),
            ("We recommend the Agent Development Kit.", True),
            ("adk-python is great.", True),
            ("Using adk python library.", True),
            ("Built with adk-js.", True),
            ("adk js is the way.", True),
            ("adk-java implementation.", True),
            ("adk java support.", True),
            ("adk-go is fast.", True),
            ("adk go patterns.", True),
            ("Just a random text.", False),
            ("gradk should not match.", False),
            ("badk matching test.", False),
            ("Using ADK.", True),  # Case insensitivity check 1
            ("AGENT DEVELOPMENT KIT", True),  # Case insensitivity check 2
        ],
    )
    def test_was_adk_mentioned(self, text, expected):
        result = VibeshareResult(
            category="test", prompt="test", model_name="test-model", response=text
        )
        assert result.was_adk_mentioned == expected

    @pytest.mark.parametrize(
        "text, expected_frameworks",
        [
            ("I used LangChain and CrewAI.", ["langchain", "crewai"]),
            ("Built with LangGraph.", ["langgraph"]),
            ("Comparing AutoGen and Semantic Kernel.", ["autogen", "semantic kernel"]),
            ("Using vertex ai agent builder.", ["vertex ai"]),
            ("No frameworks here.", []),
            (
                "LangChain is good, but langchain is better.",
                ["langchain"],
            ),  # Deduplication check (conceptually, though list might have dupes if regex finds multiple, let's see implementation behavior - implementation finds unique because loop iterates over frameworks list)
            ("Using OpenAI Assistants API.", ["openai assistants"]),
            ("Mentioning ADK and LangChain.", ["langchain", "adk"]),
        ],
    )
    def test_mentioned_frameworks(self, text, expected_frameworks):
        result = VibeshareResult(
            category="test", prompt="test", model_name="test-model", response=text
        )
        detected = result.mentioned_frameworks
        # Sort for comparison as order might depend on FRAMEWORKS_TO_DETECT list order
        assert sorted(detected) == sorted(expected_frameworks)

    def test_empty_response(self):
        result = VibeshareResult(
            category="test", prompt="test", model_name="test-model", response=None
        )
        assert result.was_adk_mentioned == False
        assert result.mentioned_frameworks == []
