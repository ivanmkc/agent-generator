# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for AnswerGenerators."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from unittest.mock import patch

import pytest

from benchmarks.answer_generators import AdkAnswerGenerator
from benchmarks.answer_generators import GeminiAnswerGenerator
from benchmarks.answer_generators import GeminiCliAnswerGenerator
from benchmarks.answer_generators import GroundTruthAnswerGenerator
from benchmarks.answer_generators import TrivialAnswerGenerator
from benchmarks.data_models import AnswerTemplate
from benchmarks.data_models import ApiUnderstandingBenchmarkCase
from benchmarks.data_models import CodeSnippetRef
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.data_models import StringMatchAnswer


@pytest.fixture
def mock_api_case() -> ApiUnderstandingBenchmarkCase:
    """Returns a mock ApiUnderstandingBenchmarkCase for testing."""
    return ApiUnderstandingBenchmarkCase(
        id="test:mock_api_case",
        description="A test case.",
        question="What is the class for a session?",
        rationale="To test the generator.",
        category="Data Models",
        file=Path("src/google/adk/sessions/session.py"),
        template=AnswerTemplate.CLASS_DEFINITION,
        answers=[
            StringMatchAnswer(
                answer="class Session(BaseModel):",
                answer_template="StringMatchAnswer",
                fully_qualified_class_name=["google.adk.sessions.session"],
            )
        ],
    )


@pytest.mark.asyncio
async def test_ground_truth_answer_generator(
    mock_api_case: ApiUnderstandingBenchmarkCase,
):
    """Tests that the GroundTruthAnswerGenerator returns the correct answer."""
    generator = GroundTruthAnswerGenerator()
    generated_answer = await generator.generate_answer(mock_api_case, run_id="test_run")
    assert generated_answer.output.code == "class Session(BaseModel):"
    assert generated_answer.output.rationale == "Ground truth answer."


@pytest.mark.asyncio
async def test_trivial_answer_generator(
    mock_api_case: ApiUnderstandingBenchmarkCase,
):
    """Tests that the TrivialAnswerGenerator returns a trivial answer."""
    generator = TrivialAnswerGenerator()
    generated_answer = await generator.generate_answer(mock_api_case, run_id="test_run")
    assert generated_answer.output.code == "class Trivial:"
    assert generated_answer.output.rationale == "Trivial answer."


@pytest.mark.asyncio
async def test_gemini_answer_generator(
    mock_api_case: ApiUnderstandingBenchmarkCase,
):
    """Tests that the GeminiAnswerGenerator returns the mocked response."""
    generator = GeminiAnswerGenerator()
    
    # We need an ApiKeyManager
    from benchmarks.api_key_manager import ApiKeyManager
    generator.api_key_manager = MagicMock(spec=ApiKeyManager)
    generator.api_key_manager.get_key_for_run.return_value = ("test-key", "key-id")

    with patch(
        "benchmarks.answer_generators.gemini_answer_generator.genai.Client"
    ) as mock_client:
        mock_response = MagicMock() 
        mock_response.text = (
            '{"code": "class Session(BaseModel):", "rationale": "mocked rationale",'
            ' "fully_qualified_class_name": "google.adk.sessions.session"}'
        )
        # Mocking model_dump and usage_metadata for Pydantic validation
        mock_response.model_dump = lambda **kwargs: {}
        mock_response.usage_metadata.total_token_count = 100
        mock_response.usage_metadata.prompt_token_count = 50
        mock_response.usage_metadata.candidates_token_count = 50
        
        mock_client.return_value.aio.models.generate_content = AsyncMock(return_value=mock_response)
        
        generated_answer = await generator.generate_answer(mock_api_case, run_id="test_run")

        assert generated_answer.output.code == "class Session(BaseModel):"
        assert generated_answer.output.rationale == "mocked rationale"
        assert (
            generated_answer.output.fully_qualified_class_name
            == "google.adk.sessions.session"
        )


@pytest.mark.asyncio
async def test_gemini_cli_answer_generator(
    mock_api_case: ApiUnderstandingBenchmarkCase,
):
    """Tests that the GeminiCliAnswerGenerator correctly parses CLI output."""
    generator = GeminiCliAnswerGenerator()
    
    from benchmarks.api_key_manager import ApiKeyManager
    generator.api_key_manager = MagicMock(spec=ApiKeyManager)
    generator.api_key_manager.get_key_for_run.return_value = ("test-key", "key-id")

    # The CLI output is expected to be a JSON string representing the ApiUnderstandingAnswerOutput
    # Wrap it in a dict because run_cli_command returns a tuple(dict, logs)
    # And the dict should have a 'response' key for model output
    model_output = (
        '{"code": "class Session(BaseModel):", "rationale": "cli rationale",' 
        ' "fully_qualified_class_name": "google.adk.sessions.session"}'
    )
    cli_response_dict = {"response": model_output}

    with patch.object(
        generator, "run_cli_command", return_value=(cli_response_dict, [])
    ) as mock_run_cli:
        generated_answer = await generator.generate_answer(mock_api_case, run_id="test_run")

        assert generated_answer.output.code == "class Session(BaseModel):"
        assert generated_answer.output.rationale == "cli rationale"
        assert (
            generated_answer.output.fully_qualified_class_name
            == "google.adk.sessions.session"
        )
        mock_run_cli.assert_called_once()


project_root = Path(__file__).parents[3]


@pytest.mark.asyncio
async def test_gemini_answer_generator_multiple_choice_with_snippet():
    """Tests GeminiAnswerGenerator with a MultipleChoiceBenchmarkCase containing a code snippet."""

    # Create a dummy snippet file
    snippet_file = project_root / "dummy_snippet.py"
    with open(snippet_file, "w") as f:
        f.write(
            "# --8<-- [start:test_section]\n# Header\nprint('Hello')\n# --8<--" 
            " [end:test_section]\n"
        )

    try:
        case = MultipleChoiceBenchmarkCase(
            id="test:mc_with_snippet",
            question="What does this code do?",
            options={"A": "Prints Hello", "B": "Nothing"},
            correct_answer="A",
            code_snippet_ref=CodeSnippetRef(
                file="dummy_snippet.py", section="test_section"
            ),
        )

        with patch(
            "benchmarks.answer_generators.gemini_answer_generator.genai.Client"
        ) as mock_client:
            mock_response = MagicMock()
            mock_response.text = '{"answer": "A", "rationale": "mocked rationale"}'
            mock_response.model_dump = lambda **kwargs: {}
            mock_response.usage_metadata.total_token_count = 100
            mock_response.usage_metadata.prompt_token_count = 50
            mock_response.usage_metadata.candidates_token_count = 50
            
            mock_client.return_value.aio.models.generate_content = AsyncMock(return_value=mock_response)
            
            generator = GeminiAnswerGenerator()
            from benchmarks.api_key_manager import ApiKeyManager
            generator.api_key_manager = MagicMock(spec=ApiKeyManager)
            generator.api_key_manager.get_key_for_run.return_value = ("test-key", "key-id")
            
            generated_answer = await generator.generate_answer(case, run_id="test_run")

            assert generated_answer.output.answer == "A"
            assert generated_answer.output.rationale == "mocked rationale"

            # Verify that the code snippet was included in the prompt
            args, kwargs = mock_client.return_value.aio.models.generate_content.call_args
            # model is kwarg, contents is arg
            prompt = kwargs.get("contents")
            assert "print('Hello')" in prompt
            assert "Header" in prompt

    finally:
        if snippet_file.exists():
            os.remove(snippet_file)


@pytest.mark.asyncio
async def test_adk_answer_generator(
    mock_api_case: ApiUnderstandingBenchmarkCase,
):
    """
    Tests that AdkAnswerGenerator correctly handles the flow and returns
    a result using its internal agents.
    """
    # Mock the agent
    from google.adk.agents import BaseAgent
    mock_agent = MagicMock(spec=BaseAgent)
    mock_agent.name = "test_agent"

    generator = AdkAnswerGenerator(agent=mock_agent, name="test_adk_gen")

    # Mock the internal agent execution
    mock_response_output = {
        "benchmark_type": "api_understanding",
        "code": "class Session(BaseModel):",
        "rationale": "adk rationale",
        "fully_qualified_class_name": "google.adk.sessions.session",
    }

    with patch.object(
        generator, "_run_agent_async", new_callable=AsyncMock
    ) as mock_run_agent:
        from benchmarks.data_models import UsageMetadata

        mock_run_agent.return_value = (
            json.dumps(mock_response_output),
            [],
            UsageMetadata(total_tokens=100)
        )
        
        # Need api_key_manager
        from benchmarks.api_key_manager import ApiKeyManager
        generator.api_key_manager = MagicMock(spec=ApiKeyManager)
        generator.api_key_manager.get_key_for_run.return_value = ("test-key", "key-id")

        result = await generator.generate_answer(mock_api_case, run_id="test_run")

        assert result.output.code == "class Session(BaseModel):"
        assert result.output.rationale == "adk rationale"
        assert (
            result.output.fully_qualified_class_name == "google.adk.sessions.session"
        )