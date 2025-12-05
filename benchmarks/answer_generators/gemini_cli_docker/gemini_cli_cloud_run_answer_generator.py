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

"""An AnswerGenerator that calls a Gemini CLI hosted on Cloud Run."""

import asyncio
import fnmatch
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Google Cloud API imports
import google.auth
import google.auth.transport.requests
import google.oauth2.id_token
from google.api_core import exceptions as api_exceptions
from google.cloud import storage
from google.cloud.devtools.cloudbuild_v1.types import Source, StorageSource
from google.cloud.run_v2 import (
    Service,
    ServicesClient,
    Container,
    RevisionTemplate,
    RevisionScaling,
    TrafficTarget,
    TrafficTargetAllocationType,
)
from google.protobuf import duration_pb2

# Custom utilities
from benchmarks.answer_generators import cloud_deploy_utils
from benchmarks.answer_generators.gemini_cli_answer_generator import (
    GeminiCliAnswerGenerator,
)
from benchmarks.data_models import TraceLogEvent
from benchmarks.utils import parse_cli_stream_json_output


class GeminiCliCloudRunAnswerGenerator(GeminiCliAnswerGenerator):
  """An AnswerGenerator that calls a Gemini CLI hosted on Cloud Run."""

  def __init__(
      self,
      dockerfile_dir: str | Path,
      service_name: str,
      model_name: str = "gemini-2.5-pro",
      project_id: str | None = None,
      region: str = "us-central1",
      context_instruction: str | None = None,
      auto_deploy: bool = False,
  ):
    """
    Args:
        dockerfile_dir: Path to the directory containing the Dockerfile to deploy.
        service_name: Name of the Cloud Run service.
        model_name: The model name.
        project_id: Google Cloud Project ID. Auto-detected if None.
        region: Cloud Run region.
        context_instruction: Instruction to prepend.
        auto_deploy: If True, automatically deploys/updates the service in setup().
    """
    super().__init__(model_name=model_name, cli_path="gemini")
    self.dockerfile_dir = Path(dockerfile_dir)
    self.service_name = service_name
    self.service_url = None  # Resolved in setup()
    self.project_id = project_id
    self.region = region
    self.context_instruction = context_instruction
    self.auto_deploy = auto_deploy
    self._auth_req = google.auth.transport.requests.Request()
    self._id_token = None
    self._id_token_time = 0
    self._remote_version = None

  @property
  def name(self) -> str:
    variant = self.service_name
    
    return (
        f"GeminiCliCloudRunAnswerGenerator({self.model_name},"
        f" variant={variant})"
    )

  def _calculate_source_hash(self, directory: Path) -> str:
    """Calculates a deterministic hash of the source directory."""
    sha = hashlib.sha256()

    # Try to read .gitignore
    ignore_patterns = [
        ".git",
        "__pycache__",
        ".ipynb_checkpoints",
        "node_modules",
        "venv",
    ]
    gitignore_path = directory / ".gitignore"
    if gitignore_path.exists():
      try:
        with open(gitignore_path, "r") as f:
          for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
              ignore_patterns.append(line)
      except Exception:
        pass  # Ignore errors reading .gitignore

    for root, dirs, files in os.walk(directory):
      # Sort in-place to ensure deterministic walk order
      dirs.sort()
      files.sort()

      # Prune ignored dirs
      i = 0
      while i < len(dirs):
        d = dirs[i]
        rel_path = (Path(root) / d).relative_to(directory).as_posix()

        should_ignore = False
        # Check against simple name matches first (common case)
        if d in ignore_patterns:
          should_ignore = True
        else:
          # Check patterns
          for pattern in ignore_patterns:
            if fnmatch.fnmatch(d, pattern) or fnmatch.fnmatch(
                rel_path, pattern
            ):
              should_ignore = True
              break

        if should_ignore:
          del dirs[i]
        else:
          i += 1

      for file in files:
        if (
            file
            in (
                "version.txt",
                ".DS_Store",
                "package-lock.json",
                "npm-debug.log",
            )
            or file.endswith(".pyc")
        ):
          continue

        rel_path = (Path(root) / file).relative_to(directory).as_posix()
        should_ignore = False
        for pattern in ignore_patterns:
          if fnmatch.fnmatch(file, pattern) or fnmatch.fnmatch(
              rel_path, pattern
          ):
            should_ignore = True
            break

        if should_ignore:
          continue

        path = Path(root) / file
        # Hash path (relative) and content
        sha.update(rel_path.encode())
        try:
          with open(path, "rb") as f:
            while True:
              chunk = f.read(4096)
              if not chunk:
                break
              sha.update(chunk)
        except OSError:
          pass  # Skip if unreadable
    return sha.hexdigest()

  async def setup(self) -> None:
    """Checks service health or deploys from source if needed."""

    # 1. Calculate local hash if we have source
    local_hash = None
    if self.dockerfile_dir and self.dockerfile_dir.exists():
      local_hash = self._calculate_source_hash(self.dockerfile_dir)
      print(f"  - Local source hash: {local_hash[:8]}")

    # Resolve Project ID early
    if not self.project_id:
      _, project_id = google.auth.default()
      self.project_id = project_id
      if self.project_id:
        print(
            f"  - Auto-detected Project ID via google.auth: {self.project_id}"
        )
      else:
        raise RuntimeError(
            "Could not determine Google Cloud Project ID. Please set"
            " GOOGLE_CLOUD_PROJECT or configure gcloud."
        )

    # 2. Resolve service URL (always try to find it)
    if not self.service_url:
      try:
        print(f"  - Resolving URL for service '{self.service_name}'...")
        client = ServicesClient()
        name = (
            f"projects/{self.project_id}/locations/{self.region}/services/{self.service_name}"
        )
        service = await asyncio.to_thread(client.get_service, name=name)
        if service.uri:
          self.service_url = service.uri
          print(f"    -> Found existing service: {self.service_url}")
      except api_exceptions.NotFound:
        print(f"    -> Service '{self.service_name}' not found.")
      except Exception as e:
        print(
            "  ! Warning: Could not retrieve existing service URL via Python"
            f" API: {e}"
        )

    if not self.service_url and not self.auto_deploy:
      print(
          "  ! Warning: No Service URL found and auto_deploy=False. Generator"
          " may fail."
      )
      return

    # Helper for HTTP checks
    def check_health(endpoint: str = "/") -> tuple[int, str] | None:
      if not self.service_url:
        return None

      token = self._get_id_token()

      url = f"{self.service_url}{endpoint}"
      req = urllib.request.Request(url, method="GET")
      if token:
        req.add_header("Authorization", f"Bearer {token}")

      try:
        with urllib.request.urlopen(req, timeout=10) as response:
          return response.status, response.read().decode("utf-8")
      except Exception:
        return None

    # 3. Check Remote Version
    remote_version = None
    if self.service_url:
      health_result = await asyncio.to_thread(check_health, endpoint="/version")
      if health_result and health_result[0] == 200:
        remote_version = health_result[1].strip()
        self._remote_version = remote_version
        print(
            f"  - Remote service version: {remote_version[:8] if remote_version else 'unknown'}"
        )
      else:
        print("  - Remote service unreachable or no version endpoint.")

    # 4. Decide Action
    if self.auto_deploy and self.dockerfile_dir:
      if local_hash == remote_version:
        print("    -> Versions match. Skipping deployment.")
      else:
        print(
            f"    -> Version mismatch (Local: {local_hash[:8]}, Remote:"
            f" {remote_version[:8] if remote_version else 'None'})."
            " Deploying..."
        )
        self.service_url = await self._deploy_from_source(
            version_id=local_hash
        )
        self._remote_version = local_hash
    elif not self.service_url:
      print("  ! Error: No service URL and deployment skipped.")

    # 5. Final verification
    if self.service_url:
      print(f"  - Target Service: {self.service_url}")

  async def _deploy_from_source(self, version_id: str) -> str:
    """Builds and deploys the service using Cloud Build and Cloud Run APIs."""
    if not self.dockerfile_dir or not self.dockerfile_dir.exists():
      raise RuntimeError(
          f"Dockerfile directory not found: {self.dockerfile_dir}"
      )

    version_file = self.dockerfile_dir / "version.txt"

    try:
      with open(version_file, "w") as f:
        f.write(version_id)

      # Project ID should be resolved in setup()
      if not self.project_id:
        raise RuntimeError("Project ID not resolved during setup.")

      # Stage 1: Build Images using Cloud Build API
      print(f"    -> Archiving and uploading source for build...")
      repo_root = self.dockerfile_dir.parent  # The gemini_cli_docker directory

      # Create a staging bucket if it doesn't exist
      staging_bucket_name = f"{self.project_id}-adk-benchmark-staging"
      storage_client = storage.Client(
          project=self.project_id, credentials=google.auth.default()[0]
      )
      bucket = storage_client.bucket(staging_bucket_name)
      if not bucket.exists():
        print(f"    -> Creating GCS staging bucket: {staging_bucket_name}")
        bucket.create(location=self.region)  # Use region for bucket location

      print(f"    -> Submitting Cloud Build for project {self.project_id}...")

      build_op = await asyncio.to_thread(
          cloud_deploy_utils.build_and_push_docker_images,
          project_id=self.project_id,
          staging_bucket=staging_bucket_name,
          repo_root=repo_root,
      )

      print(
          "    -> Waiting for Cloud Build to complete (this may take several"
          " minutes)..."
      )
      # build_op is now directly the Build object
      build_result = build_op  # Correctly assigned

      print(f"    -> Cloud Build Log URL: {build_result.log_url}")
      print(f"    -> Cloud Build Logs Bucket: {build_result.logs_bucket}")

      print("    -> Build successful.")

      # Extract image name from build result
      image_name = None
      expected_image_full_name = (
          f"gcr.io/{self.project_id}/adk-gemini-sandbox:latest"
      )

      print(f"    [debug] Build Result Images: {build_result.images}")

      for img_name_str in build_result.images:
        if img_name_str == expected_image_full_name:
          image_name = img_name_str
          break

      if not image_name:
        raise RuntimeError(
            f"Could not find expected image '{expected_image_full_name}' in"
            " build results."
        )

      # Stage 2: Deploy to Cloud Run using Cloud Run API
      print(
          f"    -> Deploying image {image_name} to Cloud Run service"
          f" {self.service_name}..."
      )

      client = ServicesClient()
      service_name_full = (
          f"projects/{self.project_id}/locations/{self.region}/services/{self.service_name}"
      )

      # Define the service configuration
      service = Service(
          template=RevisionTemplate(
              containers=[
                  Container(
                      image=image_name,
                      command=["python3"],
                      args=["/usr/local/bin/cli_server.py"],
                  )
              ],
              scaling=RevisionScaling(
                  min_instance_count=0,
                  max_instance_count=1,
              ),
          ),
          traffic=[
              TrafficTarget(
                  percent=100,
                  type_=TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST,
              )
          ],
          # Allow unauthenticated access. Note: In a production environment, you might use IAM for stricter control.
      )

      # Check if service exists
      existing_service = None
      try:
        existing_service = await asyncio.to_thread(
            client.get_service, name=service_name_full
        )
      except api_exceptions.NotFound:
        pass

      if existing_service:
        print(f"    -> Updating existing service '{self.service_name}'...")
        service.name = service_name_full
        operation = await asyncio.to_thread(
            client.update_service, service=service
        )
      else:
        print(f"    -> Creating new service '{self.service_name}'...")
        # For creation, service.name must be empty. It is derived from parent + service_id.
        operation = await asyncio.to_thread(
            client.create_service,
            parent=f"projects/{self.project_id}/locations/{self.region}",
            service_id=self.service_name,
            service=service,
        )

      print("    -> Waiting for Cloud Run deployment to complete...")
      response = await asyncio.to_thread(
          operation.result
      )  # Wait for the LRO to complete

      self.service_url = response.uri
      print(f"    -> Deployed successfully. URL: {self.service_url}")
      return self.service_url

    finally:
      if version_file.exists():
        version_file.unlink()

  def _get_id_token(self) -> str | None:
    """Obtains an ID token, trying google-auth first, then gcloud fallback.
    Caches the token for 50 minutes.
    """
    # Check if cached token is valid (assuming 1h lifetime, refresh after 50m)
    if self._id_token and (time.time() - self._id_token_time < 3000):
      return self._id_token

    token = None
    # 1. Try standard google-auth (Works for Service Accounts & Metadata Server)
    try:
      token = google.oauth2.id_token.fetch_id_token(
          self._auth_req, self.service_url
      )
    except Exception:
      # If google-auth fails (e.g. User Account with audience), fall back to gcloud
      pass

    if not token:
      # 2. Fallback: Try gcloud (Works for User Accounts locally)
      try:
        # For user accounts, we do not pass --audience.
        # Cloud Run accepts the standard user ID token.
        token = subprocess.check_output(
            ["gcloud", "auth", "print-identity-token"], encoding="utf-8"
        ).strip()
      except Exception as e:
        print(f"Warning: Could not fetch ID token: {e}")
        return None

    if token:
      self._id_token = token
      self._id_token_time = time.time()

    return token

  async def _run_cli_command(
      self, prompt: str
  ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
    """Sends the command to the Cloud Run service."""

    full_prompt = prompt
    if self.context_instruction:
      full_prompt = self.context_instruction + prompt

    # Args for the CLI
    gemini_args = [
        self.cli_path,  # "gemini"
        full_prompt,
        "--output-format",
        "stream-json",
        "--model",
        self.model_name,
        "--yolo",
    ]

    payload = {
        "args": gemini_args,
        "env": {
            "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
            "GOOGLE_GENAI_USE_VERTEXAI": os.environ.get(
                "GOOGLE_GENAI_USE_VERTEXAI", ""
            ),
            "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
            "GOOGLE_CLOUD_LOCATION": os.environ.get(
                "GOOGLE_CLOUD_LOCATION", ""
            ),
        },
    }
    # Note: Passing credentials explicitly (like API Key) is done via payload env.
    # ADC handling on the server side depends on the Service Account.

    logs: list[TraceLogEvent] = []

    def make_request():
      # Get ID Token for authentication
      token = self._get_id_token()

      req = urllib.request.Request(
          self.service_url,
          data=json.dumps(payload).encode("utf-8"),
          headers={"Content-Type": "application/json"},
          method="POST",
      )
      if token:
        req.add_header("Authorization", f"Bearer {token}")

      try:
        with urllib.request.urlopen(req) as response:
          return response.read().decode("utf-8"), response.status
      except urllib.error.HTTPError as e:
        return e.read().decode("utf-8"), e.code

    # Run blocking I/O in thread
    response_body, status_code = await asyncio.to_thread(make_request)

    if status_code != 200:
      raise RuntimeError(
          f"Cloud Run execution failed ({status_code}): {response_body}"
      )

    # Response body is JSON: { "stdout": ..., "stderr": ..., "returncode": ... }
    try:
      data = json.loads(response_body)
    except json.JSONDecodeError:
      raise RuntimeError(f"Invalid JSON from Cloud Run: {response_body}")

    stdout_str = data.get("stdout", "")
    stderr_str = data.get("stderr", "")
    returncode = data.get("returncode", 0)

    # Parse stdout using the new utility function
    response_dict, logs = parse_cli_stream_json_output(stdout_str)

    if stderr_str:
      logs.append(
          TraceLogEvent(
              type="CLOUD_RUN_STDERR", source="cloud_run", content=stderr_str
          )
      )

    if returncode != 0:
      raise RuntimeError(
          f"Gemini CLI (Cloud Run) failed with code {returncode}: {stderr_str}"
      )

    return response_dict, logs
