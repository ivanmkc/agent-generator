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
from unittest.mock import MagicMock
from unittest.mock import patch
from pathlib import Path

import pytest
from google.api_core import exceptions as api_exceptions
from google.cloud import storage

from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_cloud_run_answer_generator import \
    GeminiCliCloudRunAnswerGenerator
from benchmarks.data_models import AnswerTemplate
from benchmarks.data_models import ApiUnderstandingBenchmarkCase
from benchmarks.data_models import TraceLogEvent


@pytest.mark.asyncio
async def test_cloud_run_generator_generate_answer():
  """Test that the generator correctly calls the Cloud Run service and parses the response."""

  generator = GeminiCliCloudRunAnswerGenerator(
      dockerfile_dir=".",
      service_name="test-service",
      model_name="gemini-2.5-flash",
  )
  # Manually set service_url as it's resolved in setup() usually
  generator.service_url = "https://mock-service.run.app"

  # Mock case
  case = ApiUnderstandingBenchmarkCase(
      name="Test",
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
      json.dumps({
          "type": "message",
          "data": {"role": "model", "content": model_response_text},
      })
      + "\n"
      + json.dumps({"type": "result", "data": {"stats": {"foo": "bar"}}})
  )

  service_response_body = json.dumps({
      "stdout": cli_stdout,
      "stderr": "",
      "returncode": 0,
  })

  # Mock urlopen context manager
  with patch("urllib.request.urlopen") as mock_urlopen:
    mock_response = MagicMock()
    mock_response.read.return_value = service_response_body.encode("utf-8")
    mock_response.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # Mock auth token fetching
    with patch.object(generator, "_get_id_token", return_value="mock-token"):

      # Run generation
      result = await generator.generate_answer(case)

      # Verify request construction
      call_args = mock_urlopen.call_args
      assert call_args is not None
      req = call_args[0][0]  # The Request object

      assert req.full_url == "https://mock-service.run.app"
      assert req.get_header("Authorization") == "Bearer mock-token"
      
      # Verify payload
      payload = json.loads(req.data)
      assert "args" in payload
      assert payload["args"][0] == "gemini"
      assert "--output-format" in payload["args"]
      
      # Verify Env vars passed
      assert "env" in payload
      
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
      project_id="test-project"
  )

  # Mock google.auth.default
  with patch("google.auth.default", return_value=(None, "test-project")):
      
      # Mock ServicesClient
      with patch("benchmarks.answer_generators.gemini_cli_docker.gemini_cli_cloud_run_answer_generator.ServicesClient") as MockServicesClient:
          mock_client = MockServicesClient.return_value
          
          # Mock get_service returning a service with URI
          mock_service = MagicMock()
          mock_service.uri = "https://resolved-url.run.app"
          
          # Since setup calls await asyncio.to_thread(client.get_service, ...), 
          # mocking client.get_service is sufficient. 
          # asyncio.to_thread runs the synchronous function in a thread.
          mock_client.get_service.return_value = mock_service
          
          # Mock health check (urlopen)
          with patch("urllib.request.urlopen") as mock_urlopen:
              mock_response = MagicMock()
              mock_response.status = 200
              mock_response.read.return_value = b"version-id"
              mock_urlopen.return_value.__enter__.return_value = mock_response
              
              with patch.object(generator, "_get_id_token", return_value="mock-token"):
                  await generator.setup()
                  
      assert generator.service_url == "https://resolved-url.run.app"


@pytest.mark.asyncio
async def test_cloud_run_generator_deploy_on_mismatch():
  """Test that deployment is triggered when local hash differs from remote version."""
  
  generator = GeminiCliCloudRunAnswerGenerator(
      dockerfile_dir=Path("/tmp/fake-dir"),
      service_name="test-service",
      auto_deploy=True,
      project_id="test-project"
  )
  
  # Mock hashing
  with patch.object(generator, "_calculate_source_hash", return_value="new-hash"):
      
      # Mock google.auth.default
      with patch("google.auth.default", return_value=(MagicMock(), "test-project")):
          
          # Mock ServicesClient
          with patch("benchmarks.answer_generators.gemini_cli_docker.gemini_cli_cloud_run_answer_generator.ServicesClient") as MockServicesClient:
              mock_client = MockServicesClient.return_value
              
              # First call to get_service (resolution) - returns existing service
              existing_service = MagicMock()
              existing_service.uri = "https://existing.run.app"
              
              # Mock get_service. 
              # It's called twice: 1. resolution, 2. check exists before update/create (in _deploy_from_source)
              mock_client.get_service.return_value = existing_service
              
              # Mock update_service (in _deploy_from_source)
              mock_operation = MagicMock()
              mock_deploy_response = MagicMock()
              mock_deploy_response.uri = "https://deployed.run.app"
              mock_operation.result.return_value = mock_deploy_response
              mock_client.update_service.return_value = mock_operation
              
              # Mock urllib for version check - return mismatch
              with patch("urllib.request.urlopen") as mock_urlopen:
                  def urlopen_side_effect(req, **kwargs):
                      mock_resp = MagicMock()
                      mock_resp.status = 200
                      if "version" in req.full_url:
                          mock_resp.read.return_value = b"old-hash" # Mismatch!
                      else:
                          mock_resp.read.return_value = b"Ready"
                      
                      cm = MagicMock()
                      cm.__enter__.return_value = mock_resp
                      return cm
                  mock_urlopen.side_effect = urlopen_side_effect
                  
                  # Mock cloud_deploy_utils
                  with patch("benchmarks.answer_generators.cloud_deploy_utils.archive_code_and_upload") as mock_archive:
                      mock_archive.return_value = "gs://bucket/archive.tar.gz"
                      
                      with patch("benchmarks.answer_generators.cloud_deploy_utils.build_and_push_docker_images") as mock_build:
                          mock_build_result = MagicMock()
                          mock_build_result.images = ["gcr.io/test-project/adk-gemini-sandbox:latest"]
                          mock_build_result.log_url = "http://logs"
                          mock_build_result.logs_bucket = "gs://logs"
                          mock_build.return_value = mock_build_result
                          
                          # Mock google.cloud.storage.Client
                          with patch("google.cloud.storage.Client") as MockStorageClient:
                              # Mock file operations
                              with patch("pathlib.Path.exists", return_value=True):
                                  with patch("builtins.open", new_callable=MagicMock):
                                      with patch("pathlib.Path.unlink"):
                                          with patch.object(generator, "_get_id_token", return_value="mock-token"):
                                              await generator.setup()
              
              # Verify that deploy updated the URL
              assert generator.service_url == "https://deployed.run.app"
              
              # Verify update_service was called (because get_service succeeded)
              mock_client.update_service.assert_called()


def test_calculate_source_hash_logic(tmp_path):
  """Verify that source hashing is deterministic and respects ignore rules."""
  
  generator = GeminiCliCloudRunAnswerGenerator(
      dockerfile_dir=tmp_path,
      service_name="test-service"
  )
  
  # 1. Create initial state
  (tmp_path / "main.py").write_text("print('hello')")
  (tmp_path / "utils.py").write_text("def util(): pass")
  (tmp_path / ".git").mkdir()
  (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main")
  
  # Calculate initial hash
  hash1 = generator._calculate_source_hash(tmp_path)
  
  # 2. Verify Determinism (same state = same hash)
  hash2 = generator._calculate_source_hash(tmp_path)
  assert hash1 == hash2, "Hash should be deterministic"
  
  # 3. Verify Ignoring excluded files
  # Modify .git (should be ignored)
  (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/dev")
  # Add version.txt (should be ignored)
  (tmp_path / "version.txt").write_text("old-version-id")
  # Add __pycache__ (should be ignored)
  (tmp_path / "__pycache__").mkdir()
  (tmp_path / "__pycache__" / "cache.pyc").write_text("binary")
  
  hash3 = generator._calculate_source_hash(tmp_path)
  assert hash1 == hash3, "Hash changed despite only ignored files being modified"
  
  # 4. Verify Sensitivity (source change = new hash)
  (tmp_path / "main.py").write_text("print('hello world')")
  
  hash4 = generator._calculate_source_hash(tmp_path)
  assert hash1 != hash4, "Hash did not change after source modification"
