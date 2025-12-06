"""Unit tests for GeminiCliPodmanAnswerGenerator."""

import asyncio
import json
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import (
    GeminiCliPodmanAnswerGenerator,
)
from benchmarks.data_models import AnswerTemplate
from benchmarks.data_models import ApiUnderstandingBenchmarkCase


@pytest.mark.asyncio
async def test_podman_generator_run_cli_command():
  """Test that _run_cli_command constructs the correct Podman command."""
  generator = GeminiCliPodmanAnswerGenerator(
      image_name="test-image", model_name="gemini-2.5-flash"
  )

  # Mock asyncio.create_subprocess_exec
  with patch(
      "asyncio.create_subprocess_exec", new_callable=AsyncMock
  ) as mock_exec:
    # Setup mock process
    mock_process = MagicMock()
    mock_process.communicate = AsyncMock(
        return_value=(
            b'{"type": "message", "data": {"role": "model", "content": "Hello"}}',
            b"",
        )
    )
    mock_process.returncode = 0
    mock_exec.return_value = mock_process

    # Run command
    response, logs = await generator._run_cli_command("Test Prompt")

    # Assertions
    mock_exec.assert_called_once()
    call_args = mock_exec.call_args[0]

    # Check command structure
    assert call_args[0] == "podman"
    assert call_args[1] == "run"
    assert "test-image" in call_args
    assert "gemini" in call_args  # Entrypoint/Command
    assert "Test Prompt" in call_args

    # Check response parsing
    assert response["response"] == "Hello"
    assert len(logs) == 1
    assert logs[0].type == "message"


@pytest.mark.asyncio
async def test_podman_generator_env_vars():
  """Test that environment variables are passed to the Podman container."""
  generator = GeminiCliPodmanAnswerGenerator(image_name="test-image")

  with patch.dict(
      "os.environ",
      {
          "GEMINI_API_KEY": "fake-key",
          "GOOGLE_GENAI_USE_VERTEXAI": "1",
          "GOOGLE_CLOUD_PROJECT": "my-project",
      },
  ):
    with patch(
        "asyncio.create_subprocess_exec", new_callable=AsyncMock
    ) as mock_exec:
      mock_process = MagicMock()
      mock_process.communicate = AsyncMock(return_value=(b"", b""))
      mock_process.returncode = 0
      mock_exec.return_value = mock_process

      await generator._run_cli_command("prompt")

      call_args = mock_exec.call_args[0]
      # Check for env var flags
      assert "-e" in call_args
      assert "GEMINI_API_KEY" in call_args
      assert "GOOGLE_GENAI_USE_VERTEXAI" in call_args
      assert "GOOGLE_CLOUD_PROJECT" in call_args


@pytest.mark.asyncio
async def test_podman_generator_generate_answer():
  """Test the full generate_answer flow with a mock case."""
  generator = GeminiCliPodmanAnswerGenerator(image_name="test-image")

  case = ApiUnderstandingBenchmarkCase(
      name="Test Case",
      description="Test",
      category="Test",
      question="Generate code",
      rationale="Test",
      file="test.py",
      template=AnswerTemplate.CODE_BLOCK,
      answers=[],
  )

  # Mock CLI output (JSON stream)
  cli_output = (
      json.dumps({
          "type": "message",
          "data": {
              "role": "model",
              "content": json.dumps({
                  "code": "print('hello')",
                  "fully_qualified_class_name": "test",
                  "rationale": "reason",
              }),
          },
      })
      + "\n"
      + json.dumps({"type": "result", "data": {"stats": {}}})
  ).encode()

  with patch(
      "asyncio.create_subprocess_exec", new_callable=AsyncMock
  ) as mock_exec:
    mock_process = MagicMock()
    mock_process.communicate = AsyncMock(return_value=(cli_output, b""))
    mock_process.returncode = 0
    mock_exec.return_value = mock_process

    result = await generator.generate_answer(case)

    assert result.output.code == "print('hello')"
    assert result.output.rationale == "reason"
