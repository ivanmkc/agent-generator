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

"""Unit tests for GeminiCliCloudRunAnswerGenerator."""

import asyncio
import json
import os
from unittest.mock import MagicMock, AsyncMock
from unittest.mock import patch
from pathlib import Path

import pytest
from google.api_core import exceptions as api_exceptions
from google.cloud import storage
from google.cloud.run_v2 import (
    EnvVar,
    EnvVarSource,
    SecretKeySelector,
)

from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_cloud_run_answer_generator import (
    GeminiCliCloudRunAnswerGenerator,
)
from benchmarks.data_models import AnswerTemplate
from benchmarks.data_models import ApiUnderstandingBenchmarkCase
from benchmarks.data_models import TraceLogEvent
from benchmarks.api_key_manager import ApiKeyManager, KeyType


@pytest.fixture
def mock_api_key_manager():
    manager = MagicMock(spec=ApiKeyManager)
    manager.get_next_key.return_value = "mock-api-key"
    return manager


@pytest.mark.asyncio
async def test_cloud_run_generator_generate_answer(mock_api_key_manager):
    """Test that the generator correctly calls the Cloud Run service and parses the response."""
    
    mock_api_key_manager.get_key_for_run.return_value = ("test-key", "key-id")

    generator = GeminiCliCloudRunAnswerGenerator(
        dockerfile_dir=".",
        service_name="test-service",
        model_name="gemini-2.5-flash",
        image_name="test-image",
        api_key_manager=mock_api_key_manager,
    )
    # Manually set service_url as it's resolved in setup() usually
    generator.service_url = "https://mock-service.run.app"

    # Mock case
    case = ApiUnderstandingBenchmarkCase(
        description="Test",
        category="Test",
        question="Test question",
        rationale="Test",
        file="test.py",
        template=AnswerTemplate.CLASS_DEFINITION,
        answers=[],
    )

    # Prepare mock response from Cloud Run wrapper
    inner_model_json = {
        "code": "class Test:",
        "fully_qualified_class_name": "test.Test",
        "rationale": "Because.",
    }
    model_response_text = json.dumps(inner_model_json)

    # NDJSON output from Gemini CLI
    cli_stdout = (
        json.dumps(
            {
                "type": "message",
                "data": {"role": "model", "content": model_response_text},
            }
        )
        + "\n"
        + json.dumps({"type": "result", "data": {"stats": {"foo": "bar"}}})
    )

    service_response_body = json.dumps(
        {
            "stdout": cli_stdout,
            "stderr": "",
            "returncode": 0,
        }
    )

    # Mock aiohttp
    with patch("aiohttp.ClientSession") as MockSession:
        mock_session = MockSession.return_value
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = service_response_body

        # Mock post context manager
        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response
        mock_session.post.return_value = mock_post_cm

        # Mock context manager for session itself (async with aiohttp.ClientSession() as session)
        MockSession.return_value.__aenter__.return_value = mock_session

        # Mock auth token fetching
        with patch.object(
            generator, "_get_id_token", new_callable=AsyncMock
        ) as mock_get_token:
            mock_get_token.return_value = "mock-token"

            # Run generation
            result = await generator.generate_answer(case, run_id="test_run")

            # Verify request construction
            # Call args for session.post
            mock_session.post.assert_called_once()
            args, kwargs = mock_session.post.call_args

            assert args[0] == "https://mock-service.run.app"
            assert kwargs["headers"]["Authorization"] == "Bearer mock-token"

            # Verify payload
            payload = kwargs["json"]
            assert "args" in payload
            assert payload["args"][0] == "gemini"
            assert "--output-format" in payload["args"]

            # Verify Env vars passed (GEMINI_API_KEY should NOT be in payload.env anymore)
            assert "env" in payload
            assert "GEMINI_API_KEY" not in payload["env"]

            # Verify result parsing
            assert result.output.code == "class Test:"

            # Verify logs
            assert len(result.trace_logs) == 2
            assert result.trace_logs[0].type == "message"
            assert result.trace_logs[0].content == model_response_text


@pytest.mark.asyncio
async def test_cloud_run_generator_setup_resolves_url():
    """Test the setup method's URL resolution logic."""

    generator = GeminiCliCloudRunAnswerGenerator(
        dockerfile_dir=".",
        service_name="test-service",
        project_id="test-project",
        image_name="test-image",
    )

    # Mock google.auth.default
    with patch("google.auth.default", return_value=(None, "test-project")):

        # Mock calculate_source_hash to match the remote version
        with patch(
            "benchmarks.answer_generators.gemini_cli_docker.gemini_cli_cloud_run_answer_generator.calculate_source_hash",
            return_value="version-id",
        ):
            # Mock google.cloud.storage.Client to prevent actual API calls
            with patch("google.cloud.storage.Client") as MockStorageClient:
                mock_storage_client_instance = MockStorageClient.return_value
                mock_bucket = MagicMock()
                mock_bucket.exists.return_value = True  # Simulate bucket exists
                mock_storage_client_instance.bucket.return_value = mock_bucket

                # Mock ServicesAsyncClient
                with patch(
                    "benchmarks.answer_generators.gemini_cli_docker.gemini_cli_cloud_run_answer_generator.ServicesAsyncClient"
                ) as MockServicesClient:
                    mock_client = MockServicesClient.return_value

                    # Mock get_service returning a service with URI
                    mock_service = MagicMock()
                    mock_service.uri = "https://resolved-url.run.app"

                    # get_service is now native async
                    mock_client.get_service = AsyncMock(return_value=mock_service)

                    # Mock health check (aiohttp)
                    with patch("aiohttp.ClientSession") as MockSession:
                        mock_session = MockSession.return_value
                        mock_response = AsyncMock()
                        mock_response.status = 200
                        mock_response.text.return_value = "version-id"

                        mock_get_cm = AsyncMock()
                        mock_get_cm.__aenter__.return_value = mock_response
                        mock_session.get.return_value = mock_get_cm

                        MockSession.return_value.__aenter__.return_value = mock_session

                        with patch.object(
                            generator, "_get_id_token", new_callable=AsyncMock
                        ) as mock_get_token:
                            mock_get_token.return_value = "mock-token"

                            # Mock _deploy_from_source to avoid actual Cloud Build calls
                            with patch.object(
                                generator, "_deploy_from_source", new_callable=AsyncMock
                            ) as mock_deploy:
                                mock_deploy.return_value = "https://deployed-url.run.app"
                                await generator.setup()

        assert generator.service_url == "https://resolved-url.run.app"


from benchmarks.answer_generators.hash_utils import calculate_source_hash


# TODO: Finish implementing test
@pytest.mark.asyncio
async def test_cloud_run_generator_deploy_on_mismatch():
    """Test that deployment is triggered when local hash differs from remote version."""

    generator = GeminiCliCloudRunAnswerGenerator(
        dockerfile_dir=Path("/tmp/fake-dir"),
        service_name="test-service",
        project_id="test-project",
        image_name="test-service",
    )

    # Mock hashing (patch the imported utility function where it's used in the module)
    # Actually, we should patch where it is IMPORTED in the generator module
    with patch(
        "benchmarks.answer_generators.gemini_cli_docker.gemini_cli_cloud_run_answer_generator.calculate_source_hash",
        return_value="new-hash",
    ):

        # Mock google.auth.default
        with patch("google.auth.default", return_value=(MagicMock(), "test-project")):
            # ... (rest of test logic)
            # Placeholder for test logic, ensures an indented block
            pass  # Added 'pass' to ensure an indented block


def test_calculate_source_hash_logic(tmp_path):
    """Verify that source hashing is deterministic and respects ignore rules."""

    # 1. Create initial state
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "utils.py").write_text("def util(): pass")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main")

    # Calculate initial hash
    hash1 = calculate_source_hash(tmp_path)

    # 2. Verify Determinism (same state = same hash)
    hash2 = calculate_source_hash(tmp_path)
    assert hash1 == hash2, "Hash should be deterministic"

    # 3. Verify Ignoring excluded files
    # Modify .git (should be ignored)
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/dev")
    # Add version.txt (should be ignored)
    (tmp_path / "version.txt").write_text("old-version-id")
    # Add __pycache__ (should be ignored)
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cache.pyc").write_text("binary")

    hash3 = calculate_source_hash(tmp_path)
    assert hash1 == hash3, "Hash changed despite only ignored files being modified"

    # 4. Verify Sensitivity (source change = new hash)
    (tmp_path / "main.py").write_text("print('hello world')")

    hash4 = calculate_source_hash(tmp_path)
    assert hash1 != hash4, "Hash did not change after source modification"
