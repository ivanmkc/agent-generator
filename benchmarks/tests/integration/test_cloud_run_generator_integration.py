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

"""Real integration tests for GeminiCliCloudRunAnswerGenerator (requires deployed service)."""

import os
from pathlib import Path
import pytest
import subprocess
from google.api_core import exceptions as api_exceptions

from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_cloud_run_answer_generator import (
    GeminiCliCloudRunAnswerGenerator,
)
from benchmarks.tests.integration.predefined_cases import SIMPLE_API_UNDERSTANDING_CASE


def gcloud_available():
  try:
    subprocess.run(
        ["gcloud", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return True
  except (FileNotFoundError, subprocess.CalledProcessError):
    return False


@pytest.mark.asyncio
@pytest.mark.skipif(not gcloud_available(), reason="gcloud CLI not available")
async def test_cloud_run_generator_real_integration():
  """
  Tests the GeminiCliCloudRunAnswerGenerator by deploying from source.
  Requires GOOGLE_CLOUD_PROJECT (or gcloud config) and GEMINI_API_KEY env vars.
  """
  gemini_api_key = os.environ.get("GEMINI_API_KEY")
  project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
  
  print("\n--- Starting Cloud Run Integration Test ---")

  if not project_id:
      # Try to infer from gcloud
      print("  - Attempting to infer project ID from gcloud...")
      try:
          res = subprocess.run(
              ["gcloud", "config", "get-value", "project"],
              capture_output=True, text=True, check=True
          )
          project_id = res.stdout.strip()
          print(f"  - Inferred Project ID: {project_id}")
      except subprocess.CalledProcessError:
          print("  ! Failed to infer project ID.")
          pass

  if not gemini_api_key:
    pytest.fail("GEMINI_API_KEY environment variable not set.")
  if not project_id:
    pytest.fail("Could not determine Google Cloud Project ID (set GOOGLE_CLOUD_PROJECT or run 'gcloud config set project').")

  print(f"  - Project ID: {project_id}")
  print("  - Prerequisites checked.")

  dockerfile_dir = Path(
      "benchmarks/answer_generators/gemini_cli_docker/adk-python"
  )
  if not dockerfile_dir.exists():
      pytest.fail(f"Dockerfile directory not found: {dockerfile_dir}")

  print(f"  - Dockerfile Directory: {dockerfile_dir}")

  generator = GeminiCliCloudRunAnswerGenerator(
      dockerfile_dir=dockerfile_dir,
      service_name="adk-gemini-sandbox",
      project_id=project_id, # Pass project_id explicitly
      auto_deploy=True,
      model_name="gemini-2.5-flash",
  )

  # Setup will trigger deployment if needed
  print("  - Starting generator setup (this may include build and deployment)...")
  try:
      await generator.setup()
      print("  - Generator setup complete.")
  except (RuntimeError, api_exceptions.Forbidden, Exception) as e:
      print(f"DEBUG: Full exception details: {e}")
      if "Build failed" in str(e):
          pytest.fail(f"Cloud Run deployment failed during build. Check Cloud Build logs for details. Error: {e}")
      else:
          pytest.fail(f"Cloud Run deployment failed during setup: {e}")

  # Run generation
  print("  - Starting answer generation for test case...")
  try:
    result = await generator.generate_answer(SIMPLE_API_UNDERSTANDING_CASE)
    print("  - Answer generation complete.")

    print("  - Verifying result...")
    assert result.output.code, "Should generate code"
    assert "Event" in result.output.fully_qualified_class_name

    # Check trace logs
    assert result.trace_logs, "Should have trace logs"
    assert any(log.source == "cloud_run" for log in result.trace_logs)
    print("  - Verification successful.")

  except Exception as e:
    pytest.fail(f"Real Cloud Run integration test failed: {e}")
