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

@pytest.mark.asyncio
async def test_podman_generator_setup(mock_subprocess):
    """Test that setup starts the server container with correct args."""
    generator = GeminiCliPodmanAnswerGenerator(
        dockerfile_dir=".",
        image_name="test-image",
        model_name="gemini-2.5-flash",
        image_definitions={},
    )

    # Mock socket to return fixed port
    with patch("socket.socket") as mock_socket:
        mock_socket.return_value.getsockname.return_value = [0, 12345] # port 12345
        
        # Mock aiohttp for health check (which now uses POST)
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status = 200
            # Return valid health check response
            mock_resp.json = AsyncMock(return_value={"returncode": 0})
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            # Mock image existence check to avoid build logic
            generator._ensure_image_ready = AsyncMock()

            await generator.setup()
            
            # Verify podman run command
            # It calls create_subprocess_exec multiple times (maybe logs?), find the 'run' one
            run_call = None
            for call in mock_subprocess.call_args_list:
                args = call[0]
                if "run" in args:
                    run_call = args
                    break
            
            assert run_call is not None
            assert "podman" in run_call
            assert "-p" in run_call
            assert "12345:8080" in run_call
            assert "test-image" in run_call
            assert "python3" in run_call
            assert "/usr/local/bin/cli_server.py" in run_call


@pytest.mark.asyncio
async def test_podman_generator_env_vars_setup(mock_subprocess):
    """Test that env vars are passed to the container at startup."""
    generator = GeminiCliPodmanAnswerGenerator(
        dockerfile_dir=".",
        image_name="test-image",
        image_definitions={},
    )
    generator._ensure_image_ready = AsyncMock()

    with patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "fake-key",
            "GOOGLE_GENAI_USE_VERTEXAI": "1",
        },
    ):
        with patch("socket.socket") as mock_socket:
            mock_socket.return_value.getsockname.return_value = [0, 12345]
            
            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"returncode": 0})
                mock_post.return_value.__aenter__.return_value = mock_resp
                
                await generator.setup()
                
                run_call = None
                for call in mock_subprocess.call_args_list:
                    args = call[0]
                    if "run" in args:
                        run_call = args
                        break
                
                assert "-e" in run_call
                assert "GEMINI_API_KEY" in run_call
                assert "GOOGLE_GENAI_USE_VERTEXAI" in run_call


@pytest.mark.asyncio
async def test_podman_generator_run_cli_command():
    """Test run_cli_command sends correct HTTP request."""
    generator = GeminiCliPodmanAnswerGenerator(
        dockerfile_dir=".",
        image_name="test-image",
        image_definitions={},
    )
    
    # Manually set up generator state to bypass setup()
    generator._setup_completed = True
    generator._base_url = "http://localhost:12345"
    
    # Mock CLI response
    mock_response_data = {
        "stdout": '{"type": "message", "data": {"role": "model", "content": "Hello"}}',
        "stderr": "",
        "returncode": 0
    }
    
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response_data)
        mock_post.return_value.__aenter__.return_value = mock_resp
        
        response, logs = await generator.run_cli_command(["gemini", "--output-format", "stream-json", "Test Prompt"])
        
        # Verify call arguments
        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args
        
        url = call_args[0]
        assert url == "http://localhost:12345"
        
        payload = call_kwargs["json"]
        assert payload["args"] == ["gemini", "--output-format", "stream-json", "Test Prompt"]
        
        # Verify response parsing
        assert len(logs) == 1
        assert logs[0].type == "message"
        assert logs[0].content == "Hello"


@pytest.mark.asyncio
async def test_podman_generator_generate_answer():
    """Test full generate_answer flow."""
    generator = GeminiCliPodmanAnswerGenerator(
        dockerfile_dir=".",
        image_name="test-image",
        image_definitions={},
    )
    generator._setup_completed = True
    generator._base_url = "http://localhost:12345"
    
    case = ApiUnderstandingBenchmarkCase(
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
    )
    
    mock_response_data = {
        "stdout": cli_stdout,
        "stderr": "",
        "returncode": 0
    }

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response_data)
        mock_post.return_value.__aenter__.return_value = mock_resp
        
        result = await generator.generate_answer(case)
        
        assert result.output.code == "print('hello')"
        assert result.output.rationale == "reason"