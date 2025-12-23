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

"""Unit tests for the answer generators."""

from pathlib import Path
import sys
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

# Ensure src is in path
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from google.adk.agents import Agent
from google.adk.events.event import Event  # Added import
from google.genai import types

from benchmarks.answer_generators import AdkAnswerGenerator
from benchmarks.answer_generators import GeminiAnswerGenerator
from benchmarks.answer_generators.gemini_cli_local_answer_generator import (
    GeminiCliLocalAnswerGenerator,
)
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
        description="A test case.",
        question="What is the class for a session?",
        rationale="To test the generator.",
        category="Data Models",
        file=Path("src/google/adk/sessions/session.py"),
        template=AnswerTemplate.CLASS_DEFINITION,
        answers=[
            StringMatchAnswer(
                answer="class Session(BaseModel):",
                line_number=42,
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
    generated_answer = await generator.generate_answer(mock_api_case)
    assert generated_answer.output.code == "class Session(BaseModel):"
    assert (
        generated_answer.output.fully_qualified_class_name
        == "google.adk.sessions.session"
    )


@pytest.mark.asyncio
async def test_trivial_answer_generator(
    mock_api_case: ApiUnderstandingBenchmarkCase,
):
    """Tests that the TrivialAnswerGenerator returns a trivial answer."""
    generator = TrivialAnswerGenerator()
    generated_answer = await generator.generate_answer(mock_api_case)
    assert generated_answer.output.code == "class Trivial:"
    assert generated_answer.output.fully_qualified_class_name == "trivial.module"


@pytest.mark.asyncio
async def test_gemini_answer_generator(
    mock_api_case: ApiUnderstandingBenchmarkCase,
):
    """Tests the GeminiAnswerGenerator with a mocked API client."""
    with patch(
        "benchmarks.answer_generators.gemini_answer_generator.genai.Client"
    ) as mock_client:
        mock_response = MagicMock()
        mock_response.text = (
            '{"code": "mocked class", "fully_qualified_class_name":'
            ' "mocked.module", "rationale": "mocked rationale"}'
        )
        mock_response.model_dump_json.return_value = '{"full_metadata": "mocked"}'
        mock_response.model_dump.return_value = {"full_metadata": "mocked"}
        # The generator uses client.aio.models.generate_content
        mock_client.return_value.aio.models.generate_content = AsyncMock(
            return_value=mock_response
        )

        generator = GeminiAnswerGenerator()
        generated_answer = await generator.generate_answer(mock_api_case)

        assert generated_answer.output.code == "mocked class"
        assert generated_answer.output.fully_qualified_class_name == "mocked.module"

        # Verify trace logs are a list of TraceLogEvent
        assert len(generated_answer.trace_logs) == 1
        assert generated_answer.trace_logs[0].type == "GEMINI_API_RESPONSE"
        assert generated_answer.trace_logs[0].details == {"full_metadata": "mocked"}

        mock_client.return_value.aio.models.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_gemini_cli_answer_generator(
    mock_api_case: ApiUnderstandingBenchmarkCase,
):
    """Tests the GeminiCliLocalAnswerGenerator with mocked subprocess execution."""
    # Mock the NDJSON output expected by parse_cli_stream_json_output
    mock_content = (
        '```json\n{"code": "cli class", "fully_qualified_class_name":'
        ' "cli.module", "rationale": "cli rationale",'
        ' "benchmark_type": "api_understanding"}\n```'
    )
    mock_cli_output = {
        "type": "message",
        "data": {"role": "model", "content": mock_content},
    }

    import json

    mock_stdout = json.dumps(mock_cli_output).encode("utf-8")

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Mock the process object
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (mock_stdout, b"")
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        generator = GeminiCliLocalAnswerGenerator()
        generated_answer = await generator.generate_answer(mock_api_case)

        # Verify parsed output
        assert generated_answer.output.code == "cli class"
        assert generated_answer.output.fully_qualified_class_name == "cli.module"

        # Verify trace logs
        assert len(generated_answer.trace_logs) == 1
        assert generated_answer.trace_logs[0].type == "message"
        assert generated_answer.trace_logs[0].content == mock_content

        # Verify CLI invocation arguments
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args[0]
        assert call_args[0] == "gemini"  # Default cli_path
        # Ensure prompt is positional (not using --prompt)
        assert (
            call_args[1] is not None
        )  # Prompt string # Wait, indices might shift due to list unfolding *cmd_args
        # command_parts = [cli_path, flags..., prompt]
        # Since we use *command_parts in subprocess_exec, call_args[0] is cli_path, call_args[1] is flag...
        assert "--prompt" not in call_args
        assert "--output-format" in call_args
        assert "stream-json" in call_args
        assert "--yolo" in call_args


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
            mock_response.model_dump_json.return_value = "{}"
            mock_response.model_dump.return_value = {}
            mock_client.return_value.aio.models.generate_content = AsyncMock(
                return_value=mock_response
            )
            generator = GeminiAnswerGenerator()
            generated_answer = await generator.generate_answer(case)

            assert generated_answer.output.answer == "A"

            # Verify prompt contains the code
            call_args = mock_client.return_value.aio.models.generate_content.call_args
            prompt = call_args.kwargs["contents"]
            assert "Code:" in prompt
            assert "print('Hello')" in prompt
            assert "# Header" in prompt

    finally:
        if snippet_file.exists():
            snippet_file.unlink()


@pytest.mark.asyncio
async def test_adk_answer_generator(
    mock_api_case: ApiUnderstandingBenchmarkCase,
):
    """Tests the AdkAnswerGenerator with a mocked ADK runner."""
    with patch(
        "benchmarks.answer_generators.adk_answer_generator.InMemoryRunner"
    ) as MockInMemoryRunner:
        mock_runner_instance = MockInMemoryRunner.return_value

        mock_runner_instance.session_service = MagicMock()
        mock_runner_instance.session_service.create_session = AsyncMock()
        mock_runner_instance.session_service.create_session.return_value = MagicMock(
            id="benchmark_session", user_id="benchmark_user"
        )

        mock_events = [
            Event(
                author="model",
                content=types.Content(
                    parts=[
                        types.Part(
                            text=(
                                '{"code": "adk class",'
                                ' "fully_qualified_class_name": "adk.module",'
                                ' "rationale": "mocked rationale"}'
                            )
                        )
                    ]
                ),
            )
        ]

        # Manually create an async generator to ensure __aiter__ behavior
        async def real_async_generator(*args, **kwargs):
            for event in mock_events:
                yield event

        call_count = 0

        async def counting_async_generator(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            async for event in real_async_generator(*args, **kwargs):
                yield event

        mock_runner_instance.run_async = counting_async_generator

        mock_agent = MagicMock(spec=Agent)
        mock_agent.name = "test_agent"
        generator = AdkAnswerGenerator(agent=mock_agent)
        generated_answer = await generator.generate_answer(mock_api_case)

        assert generated_answer.output.code == "adk class"
        assert generated_answer.output.fully_qualified_class_name == "adk.module"
        assert len(generated_answer.trace_logs) > 0
        assert generated_answer.trace_logs[0].type == "ADK_EVENT"
        assert generated_answer.trace_logs[0].content["parts"][0]["text"] == (
            '{"code": "adk class",'
            ' "fully_qualified_class_name": "adk.module",'
            ' "rationale": "mocked rationale"}'
        )
        assert call_count == 1
        mock_runner_instance.session_service.create_session.assert_called_once()
        MockInMemoryRunner.assert_called_once()
