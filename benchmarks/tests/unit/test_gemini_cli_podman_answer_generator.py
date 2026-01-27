"""Unit tests for GeminiCliPodmanAnswerGenerator."""

import asyncio
import json
import os
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import aiohttp

from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import (
    GeminiCliPodmanAnswerGenerator,
    GeminiCliExecutionError,
)
from benchmarks.data_models import AnswerTemplate
from benchmarks.data_models import ApiUnderstandingBenchmarkCase


@pytest.fixture
def mock_subprocess():
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock:
        process = MagicMock()
        process.communicate = AsyncMock(return_value=(b"", b""))
        process.returncode = 0
        mock.return_value = process
        yield mock


@pytest.fixture
def mock_akm():
    from benchmarks.api_key_manager import ApiKeyManager

    manager = MagicMock(spec=ApiKeyManager)
    manager.get_key_for_run = AsyncMock(return_value=("test-key", "key-id"))
    manager.report_result = AsyncMock()
    return manager


@pytest.fixture
def mock_container():
    with patch(
        "benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator.PodmanContainer"
    ) as mock:
        instance = mock.return_value
        instance.start = AsyncMock()
        instance.stop = MagicMock()
        instance.send_command = AsyncMock()
        instance.read_file = AsyncMock()
        instance.base_url = "http://localhost:12345"
        yield instance


@pytest.mark.asyncio
async def test_podman_generator_setup(mock_subprocess, mock_akm, mock_container):
    """Test that setup starts the server container."""
    generator = GeminiCliPodmanAnswerGenerator(
        image_name="test-image",
        model_name="gemini-2.5-flash",
        image_definitions={},
        api_key_manager=mock_akm,
    )
    generator._ensure_image_ready = AsyncMock()

    await generator.setup()

    # Verify container.start was called
    mock_container.start.assert_called_once()


@pytest.mark.asyncio
async def test_podman_generator_env_vars_setup(
    mock_subprocess, mock_akm, mock_container
):
    """Test that env vars are correctly set on the generator."""
    generator = GeminiCliPodmanAnswerGenerator(
        image_name="test-image",
        model_name="gemini-2.5-flash",
        image_definitions={},
        api_key_manager=mock_akm,
        extra_env={"CUSTOM_VAR": "custom-val"},
    )

    assert generator.extra_env["CUSTOM_VAR"] == "custom-val"


@pytest.mark.asyncio
async def test_podman_generator_run_cli_command(mock_akm, mock_container):
    """Test run_cli_command sends correct HTTP request via container."""
    generator = GeminiCliPodmanAnswerGenerator(
        image_name="test-image",
        model_name="gemini-2.5-flash",
        image_definitions={},
        api_key_manager=mock_akm,
    )

    # Manually set up generator state to bypass setup()
    generator._setup_completed = True
    generator._base_url = "http://localhost:12345"

    # Mock container response
    mock_response_data = {
        "stdout": '{"type": "message", "data": {"role": "model", "content": "Hello"}}',
        "stderr": "",
        "returncode": 0,
    }
    mock_container.send_command.return_value = mock_response_data

    response, logs = await generator.run_cli_command(
        ["gemini", "--output-format", "stream-json", "Test Prompt"]
    )

    # Verify send_command call
    mock_container.send_command.assert_called_once()
    args, kwargs = mock_container.send_command.call_args
    assert args[0] == ["gemini", "--output-format", "stream-json", "Test Prompt"]

    # Verify response parsing
    assert len(logs) == 2
    assert logs[0].type == "CLI_STDOUT_FULL"
    assert logs[1].type == "message"
    assert logs[1].content == "Hello"


@pytest.mark.asyncio
async def test_podman_generator_generate_answer(mock_akm, mock_container):
    """Test full generate_answer flow."""
    generator = GeminiCliPodmanAnswerGenerator(
        image_name="test-image",
        model_name="gemini-2.5-flash",
        image_definitions={},
        api_key_manager=mock_akm,
    )
    generator._setup_completed = True
    generator._base_url = "http://localhost:12345"

    case = ApiUnderstandingBenchmarkCase(
        id="test:podman",
        description="Test",
        category="Test",
        question="Generate code",
        rationale="Test",
        file="test.py",
        template=AnswerTemplate.CODE_BLOCK,
        answers=[],
    )

    # Mock CLI output (JSON stream)
    cli_stdout = (
        json.dumps(
            {
                "type": "message",
                "data": {
                    "role": "model",
                    "content": json.dumps(
                        {
                            "code": "print('hello')",
                            "fully_qualified_class_name": "test",
                            "rationale": "reason",
                        }
                    ),
                },
            }
        )
        + "\n"
        + json.dumps({"type": "result", "data": {"stats": {}}})
    )

    mock_response_data = {"stdout": cli_stdout, "stderr": "", "returncode": 0}
    mock_container.send_command.return_value = mock_response_data

    result = await generator.generate_answer(case, run_id="test_run")

    assert result.output.code == "print('hello')"
    assert result.output.rationale == "reason"


@pytest.mark.asyncio
async def test_run_cli_command_error_report_capture(
    mock_subprocess, mock_akm, mock_container
):
    """
    Tests that a Gemini client error report file mentioned in stderr is captured
    and added to trace logs using the /read_file API endpoint.
    """
    generator = GeminiCliPodmanAnswerGenerator(
        image_name="test-image",
        model_name="gemini-2.5-flash",
        image_definitions={},
        api_key_manager=mock_akm,
    )
    generator._setup_completed = True
    generator._base_url = "http://localhost:12345"

    error_file_path = "/tmp/gemini-client-error-123.json"
    error_file_content = '{"error": "Rate limited", "code": 429}'

    mock_container.send_command.return_value = {
        "stdout": "",
        "stderr": f"Error when talking to Gemini API Full report available at: {error_file_path}",
        "returncode": 1,
    }
    mock_container.read_file.return_value = error_file_content

    # Expected to raise GeminiCliExecutionError because returncode is 1
    with pytest.raises(GeminiCliExecutionError) as excinfo:
        await generator.run_cli_command(
            ["gemini", "--model", "gemini-flash", "Test prompt"]
        )

    error_msg = str(excinfo.value)
    assert "Gemini CLI failed with code 1" in error_msg
    assert error_file_content in error_msg

    # Verify interactions
    mock_container.send_command.assert_called_once()
    mock_container.read_file.assert_called_once_with(error_file_path)
