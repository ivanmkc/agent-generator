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

import json
import os
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_docker_answer_generator import (
    GeminiCliDockerAnswerGenerator,
)
from benchmarks.data_models import AnswerTemplate
from benchmarks.data_models import ApiUnderstandingBenchmarkCase


@pytest.mark.asyncio
async def test_docker_command_construction_api_key():
    """Test that Docker command is constructed correctly with GEMINI_API_KEY."""

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
        generator = GeminiCliDockerAnswerGenerator(
            model_name="gemini-2.5-flash",
            image_name="gemini-cli:adk-python",
        )
        generator._setup_completed = True

        # The CLI with --output-format stream-json returns NDJSON
        # We mock the NDJSON output
        ndjson_output = (
            json.dumps(
                {
                    "type": "message",
                    "data": {"role": "model", "content": "test response"},
                }
            )
            + "\n"
            + json.dumps({"type": "result", "data": {"stats": {"foo": "bar"}}})
        )
        stdout_bytes = ndjson_output.encode()

        # Mock the subprocess execution
        with patch(
            "asyncio.create_subprocess_exec", new_callable=AsyncMock
        ) as mock_exec:
            mock_proc = MagicMock()
            mock_proc.communicate = AsyncMock(return_value=(stdout_bytes, b""))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            # Create a dummy case
            case = ApiUnderstandingBenchmarkCase(
                description="Test",
                category="Test",
                question="Test question",
                rationale="Test",
                file="test.py",
                template=AnswerTemplate.CLASS_DEFINITION,
                answers=[],
            )

            # We need to mock the response schema validation because our dummy response "test response"
            # won't parse into the ApiUnderstandingAnswerOutput model.
            # However, _run_cli_command returns a dict which generate_answer then tries to parse as JSON.
            # The base GeminiCliAnswerGenerator.generate_answer expects the model output text to be a JSON string.
            # So our "test response" should essentially be that JSON string.

            inner_model_json = {
                "code": "class Test:",
                "fully_qualified_class_name": "test.Test",
                "rationale": "Because.",
            }
            model_response_text = json.dumps(inner_model_json)

            # Update NDJSON to contain this text
            ndjson_output = (
                json.dumps(
                    {
                        "type": "message",
                        "data": {"role": "model", "content": model_response_text},
                    }
                )
                + "\n"
                + json.dumps({"type": "result", "data": {"stats": {"foo": "bar"}}})
            )
            stdout_bytes = ndjson_output.encode()
            mock_proc.communicate = AsyncMock(return_value=(stdout_bytes, b""))

            await generator.generate_answer(case)

            # Verify arguments
            args, _ = mock_exec.call_args
            cmd = list(args)

            # Check for Docker parts
            assert "docker" in cmd
            assert "run" in cmd
            assert "--rm" in cmd
            assert "-e" in cmd
            assert "GEMINI_API_KEY" in cmd
            assert "gemini-cli:adk-python" in cmd

            # Check for Gemini CLI parts
            assert "gemini" in cmd
            assert "--output-format" in cmd
            assert "stream-json" in cmd  # Expect stream-json
            assert "--model" in cmd
            assert "gemini-2.5-flash" in cmd

            # Verify trace logs
            result = await generator.generate_answer(case)
            assert len(result.trace_logs) == 2

            # First log entry (message type)
            msg_log = result.trace_logs[0]
            assert msg_log.type == "message"
            assert msg_log.source == "docker"
            assert msg_log.role == "model"
            assert msg_log.content == model_response_text

            # Second log entry (result type)
            res_log = result.trace_logs[1]
            assert res_log.type == "system_result"
            assert res_log.source == "docker"
            assert res_log.content == {"foo": "bar"}


@pytest.mark.asyncio
async def test_docker_command_construction_vertex_adc():
    """Test that Docker command handles Vertex AI and ADC mounting correctly."""

    env_vars = {
        "GOOGLE_GENAI_USE_VERTEXAI": "true",
        "GOOGLE_CLOUD_PROJECT": "my-project",
        "GOOGLE_APPLICATION_CREDENTIALS": "/local/path/creds.json",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        generator = GeminiCliDockerAnswerGenerator(image_name="gemini-cli:adk-python")
        generator._setup_completed = True

        inner_model_json = {
            "code": "class Vertex:",
            "fully_qualified_class_name": "vertex.Test",
            "rationale": "Vertex logic.",
        }
        model_response_text = json.dumps(inner_model_json)

        ndjson_output = (
            json.dumps(
                {
                    "type": "message",
                    "data": {"role": "model", "content": model_response_text},
                }
            )
            + "\n"
            + json.dumps({"type": "result", "data": {"stats": {"foo": "bar"}}})
        )
        stdout_bytes = ndjson_output.encode()

        with patch(
            "asyncio.create_subprocess_exec", new_callable=AsyncMock
        ) as mock_exec:
            mock_proc = MagicMock()
            mock_proc.communicate = AsyncMock(return_value=(stdout_bytes, b""))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            case = ApiUnderstandingBenchmarkCase(
                description="Test",
                category="Test",
                question="Test",
                rationale="Test",
                file="test.py",
                template=AnswerTemplate.CLASS_DEFINITION,
                answers=[],
            )

            # Verify trace logs
            result = await generator.generate_answer(case)
            assert len(result.trace_logs) == 2

            # First log entry (message type)
            msg_log = result.trace_logs[0]
            assert msg_log.type == "message"
            assert msg_log.source == "docker"
            assert msg_log.role == "model"
            assert msg_log.content == model_response_text

            # Second log entry (result type)
            res_log = result.trace_logs[1]
            assert res_log.type == "system_result"
            assert res_log.source == "docker"
            assert res_log.content == {"foo": "bar"}

            # Check arguments
            args, _ = mock_exec.call_args
            cmd = list(args)

            # Vertex AI Env vars
            assert "GOOGLE_GENAI_USE_VERTEXAI" in cmd
            assert "GOOGLE_CLOUD_PROJECT" in cmd
            assert "GOOGLE_APPLICATION_CREDENTIALS=/tmp/google_credentials.json" in [
                arg
                for arg in cmd
                if str(arg).startswith("GOOGLE_APPLICATION_CREDENTIALS=")
            ]

            # Volume mount
            assert "-v" in cmd
            assert "/local/path/creds.json:/tmp/google_credentials.json" in cmd
