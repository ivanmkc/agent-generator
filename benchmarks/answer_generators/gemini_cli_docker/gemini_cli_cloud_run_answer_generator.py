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
from pathlib import Path
from typing import Any

import aiohttp
# Google Cloud API imports
import google.auth
import google.auth.transport.requests
import google.oauth2.id_token
from google.api_core import client_options, exceptions as api_exceptions # Added client_options
from google.cloud import storage
from google.cloud.devtools import cloudbuild_v1 # Added import
from google.cloud.devtools.cloudbuild_v1.types import Source, StorageSource
from google.cloud.run_v2 import (
    Service,
    ServicesAsyncClient,
    Container,
    ResourceRequirements,
    RevisionTemplate,
    RevisionScaling,
    TrafficTarget,
    TrafficTargetAllocationType,
    EnvVar,
    EnvVarSource,
    SecretKeySelector,
)
from google.protobuf import duration_pb2

# Custom utilities
from benchmarks.answer_generators import cloud_deploy_utils
from benchmarks.answer_generators.gemini_cli_answer_generator import (
    GeminiCliAnswerGenerator,
)
from benchmarks.config import CLOUD_RUN_CONFIG

# Cloud Build API endpoint
SERVICE_BASE_PATH = "cloudbuild.googleapis.com"

from benchmarks.data_models import TraceLogEvent
from benchmarks.utils import parse_cli_stream_json_output
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import (
    IMAGE_DEFINITIONS,
    IMAGE_PREFIX,
)
from benchmarks.answer_generators.hash_utils import calculate_source_hash


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
      image_name: str | None = None,
      force_deploy: bool = False,
      service_url: str | None = None,
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
        image_name: Optional override for the image name (excluding registry/project).
                    Defaults to service_name (with exception for adk-python).
        force_deploy: If True, forces a deployment in setup() even if versions match.
        service_url: If provided, runs in Proxy Mode using this URL without deploying.
    """
    super().__init__(model_name=model_name, cli_path="gemini")
    self.dockerfile_dir = Path(dockerfile_dir)
    self.service_name = service_name
    self.project_id = project_id
    self.region = region
    self.context_instruction = context_instruction
    self.auto_deploy = auto_deploy
    self.force_deploy = force_deploy
    self._auth_req = google.auth.transport.requests.Request()
    self._id_token = None
    self._id_token_time = 0
    self._remote_version = None

    if service_url:
        self.service_url = service_url
        self._is_proxy = True
    else:
        self.service_url = None
        self._is_proxy = False

    if image_name:
      self.image_name = image_name
    else:
      # Determine the base directory name from dockerfile_dir, e.g., 'adk-python' from '.../gemini_cli_docker/adk-python'
      docker_base_dir_name = self.dockerfile_dir.name
      
      # Find the full image name in IMAGE_DEFINITIONS that corresponds to this source directory
      found_image_key = None
      for key, definition in IMAGE_DEFINITIONS.items():
          if definition.source_dir == docker_base_dir_name:
              found_image_key = key
              break
      
      if found_image_key:
          self.image_name = found_image_key
      else:
          if not self._is_proxy: # Allow missing image def if just proxying
              raise ValueError(
                  f"Could not determine a valid image name for dockerfile_dir: {self.dockerfile_dir}. "
                  "The directory name must match a `source_dir` in `IMAGE_DEFINITIONS` or "
                  "`image_name` must be provided explicitly."
              )
          self.image_name = "unknown-proxy"

  @property
  def name(self) -> str:
    variant = self.service_name
    
    return (
        f"GeminiCliCloudRunAnswerGenerator({self.model_name},"
        f" variant={variant})"
    )

  async def setup(self) -> None:
    """Checks service health or deploys from source if needed."""
    
    if self._is_proxy:
        print(f"[CloudRun Setup] Running in Proxy Mode against {self.service_url}")
        # Resolve Project ID if not set (needed for ID token generation)
        if not self.project_id:
            _, project_id = google.auth.default()
            self.project_id = project_id
        return

    # 1. Calculate local hash if we have source
    local_hash = None
    if self.dockerfile_dir and self.dockerfile_dir.exists():
      local_hash = calculate_source_hash(self.dockerfile_dir)
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
        client = ServicesAsyncClient()
        name = (
            f"projects/{self.project_id}/locations/{self.region}/services/{self.service_name}"
        )
        service = await client.get_service(name=name)
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
    async def check_health(endpoint: str = "/") -> tuple[int, str] | None:
      if not self.service_url:
        return None

      token = await self._get_id_token()

      url = f"{self.service_url}{endpoint}"
      headers = {}
      if token:
        headers["Authorization"] = f"Bearer {token}"

      try:
        async with aiohttp.ClientSession() as session:
          async with session.get(url, headers=headers, timeout=10) as response:
            return response.status, await response.text()
      except Exception:
        return None

    # 3. Check Remote Version
    remote_version = None
    if self.service_url and not self.force_deploy:
      health_result = await check_health(endpoint="/version")
      if health_result and health_result[0] == 200:
        remote_version = health_result[1].strip()
        self._remote_version = remote_version
        print(
            f"  - Remote service version: {remote_version[:8] if remote_version else 'unknown'}"
        )
      else:
        print("  - Remote service unreachable or no version endpoint.")

    # 4. Decide Action
    should_deploy = False
    if self.auto_deploy and self.dockerfile_dir:
        if self.force_deploy:
            print("    -> Force deploy requested. Deploying...")
            should_deploy = True
        elif local_hash == remote_version:
            print("    -> Versions match. Skipping deployment.")
        else:
            print(
                f"    -> Version mismatch (Local: {local_hash[:8]}, Remote:"
                f" {remote_version[:8] if remote_version else 'None'})."
                " Deploying..."
            )
            should_deploy = True
    
    if should_deploy:
        self.service_url = await self._deploy_from_source(
            version_id=local_hash
        )
        self._remote_version = local_hash
    elif not self.service_url:
      print("  ! Error: No service URL and deployment skipped.")

    # 5. Final verification
    if self.service_url:
      print(f"  - Target Service: {self.service_url}")

  async def teardown(self) -> None:
      """Perform cleanup. No-op for persistent Cloud Run services."""
      if self._is_proxy:
          return
      # We typically don't delete Cloud Run services automatically after tests
      pass

  async def _check_secret_exists(self, secret_id: str) -> bool:
    """Checks if a secret exists in Secret Manager via gcloud."""
    # We use gcloud here to avoid adding google-cloud-secret-manager dependency
    # just for this check, assuming gcloud is available where this runs.
    try:
      proc = await asyncio.create_subprocess_exec(
          "gcloud",
          "secrets",
          "describe",
          secret_id,
          "--project",
          self.project_id,
          stdout=asyncio.subprocess.PIPE,
          stderr=asyncio.subprocess.PIPE,
      )
      await proc.communicate()
      return proc.returncode == 0
    except Exception as e:
      print(f"    ! Warning: Could not check for secret '{secret_id}': {e}")
      return False

  async def _deploy_from_source(self, version_id: str) -> str:
    """Builds and deploys the service using Cloud Build and Cloud Run APIs."""
    if not self.dockerfile_dir or not self.dockerfile_dir.exists():
      raise RuntimeError(
          f"Dockerfile directory not found: {self.dockerfile_dir}"
      )

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

    build_operation = await cloud_deploy_utils.build_and_push_docker_images(
        project_id=self.project_id,
        staging_bucket=staging_bucket_name,
        repo_root=repo_root,
        substitutions={"_VERSION": version_id},
    )

    print(
        "    -> Waiting for Cloud Build to complete (this may take several"
        " minutes)..."
    )

    try:
      # For AsyncClient operations, result() is a coroutine
      build_result = await build_operation.result(timeout=3600)

      print("    -> Build successful.")

      # Extract image name from build result
      image_name = None
      
      if ":" in self.image_name:
          expected_image_full_name = f"gcr.io/{self.project_id}/{self.image_name}"
      else:
          expected_image_full_name = (
              f"gcr.io/{self.project_id}/{self.image_name}:latest"
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

    except api_exceptions.GoogleAPICallError as e:
      print(f"    [DEBUG EXCEPTION] Type of build_operation: {type(build_operation)}")
      print(f"    [DEBUG EXCEPTION] Value of build_operation: {build_operation}")
      # If the build failed, build_operation still contains the log_url.
      # We can extract the build ID from build_operation.name.
      build_id = build_operation.operation.name.split('/')[-1]
      failing_build_log_url = (
          f"https://console.cloud.google.com/cloud-build/builds/{build_id}"
          f"?project={self.project_id}"
      )
      print(f"    ! Cloud Build FAILED. Log URL: {failing_build_log_url}")
      raise RuntimeError(
          f"Cloud Build failed. Check logs at {failing_build_log_url}. Original error: {e}"
      ) from e


    # Stage 2: Deploy to Cloud Run using Cloud Run API
    print(
        f"    -> Deploying image {image_name} to Cloud Run service"
        f" {self.service_name}..."
    )

    client = ServicesAsyncClient()
    service_name_full = (
        f"projects/{self.project_id}/locations/{self.region}/services/{self.service_name}"
    )

    # Check if secret exists
    has_api_key_secret = await self._check_secret_exists("gemini-api-key")
    
    env_vars = []
    if has_api_key_secret:
        print("    -> Found 'gemini-api-key' secret. Mounting it.")
        env_vars.append(
            EnvVar(
                name="GEMINI_API_KEY",
                value_source=EnvVarSource(
                    secret_key_ref=SecretKeySelector(
                        secret="gemini-api-key",
                        version="latest",
                    )
                ),
            )
        )
    else:
        print("    -> 'gemini-api-key' secret not found. Skipping mount.")

    # Define the service configuration
    service = Service(
        template=RevisionTemplate(
            containers=[
                Container(
                    image=image_name,
                    # Remove command override to respect ENTRYPOINT (e.g. entrypoint.sh)
                    # command=["python3"], 
                    args=["python3", "/usr/local/bin/cli_server.py"],
                    resources=ResourceRequirements(
                        limits={
                            "cpu": CLOUD_RUN_CONFIG.CPU_LIMIT,
                            "memory": CLOUD_RUN_CONFIG.MEMORY_LIMIT,
                        }
                    ),
                    env=env_vars,
                )
            ],
            scaling=RevisionScaling(
                min_instance_count=0,
                max_instance_count=CLOUD_RUN_CONFIG.MAX_INSTANCES,
            ),
            # Set per-instance concurrency to the tested stable limit.
            # Cloud Run will scale out (add instances) if load exceeds this * active_instances.
            max_instance_request_concurrency=CLOUD_RUN_CONFIG.MAX_INSTANCE_CONCURRENCY,
            timeout=duration_pb2.Duration(seconds=900), # Set request timeout to 15 minutes
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
      existing_service = await client.get_service(name=service_name_full)
    except api_exceptions.NotFound:
      pass

    if existing_service:
      print(f"    -> Updating existing service '{self.service_name}'...")
      service.name = service_name_full
      operation = await client.update_service(service=service)
    else:
      print(f"    -> Creating new service '{self.service_name}'...")
      # For creation, service.name must be empty. It is derived from parent + service_id.
      operation = await client.create_service(
          parent=f"projects/{self.project_id}/locations/{self.region}",
          service_id=self.service_name,
          service=service,
      )

    print("    -> Waiting for Cloud Run deployment to complete...")
    response = await operation.result()  # Wait for the LRO to complete

    self.service_url = response.uri
    print(f"    -> Deployed successfully. URL: {self.service_url}")
    return self.service_url

  async def _get_id_token(self) -> str | None:
    """Obtains an ID token, trying google-auth first, then gcloud fallback.
    Caches the token for 50 minutes.
    """
    # Check if cached token is valid (assuming 1h lifetime, refresh after 50m)
    if self._id_token and (time.time() - self._id_token_time < 3000):
      return self._id_token

    token = None
    # 1. Try standard google-auth (Works for Service Accounts & Metadata Server)
    # This library call is synchronous/blocking, so we offload it.
    try:
      token = await asyncio.to_thread(
          google.oauth2.id_token.fetch_id_token,
          self._auth_req,
          self.service_url,
      )
    except Exception:
      # If google-auth fails (e.g. User Account with audience), fall back to gcloud
      pass

    if not token:
      # 2. Fallback: Try gcloud (Works for User Accounts locally)
      try:
        # For user accounts, we do not pass --audience.
        # Cloud Run accepts the standard user ID token.
        proc = await asyncio.create_subprocess_exec(
            "gcloud",
            "auth",
            "print-identity-token",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
          token = stdout.decode("utf-8").strip()
        else:
          print(f"Warning: Could not fetch ID token via gcloud: {stderr.decode()}")
      except Exception as e:
        print(f"Warning: Could not fetch ID token: {e}")
        return None

    if token:
      self._id_token = token
      self._id_token_time = time.time()

    return token

  async def run_cli_command(
      self, command_parts: list[str]
  ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
    """Sends the command to the Cloud Run service."""

    # Heuristic extraction of prompt, similar to other generators
    is_generation = "--model" in command_parts
    
    final_command_parts = list(command_parts)
    
    if is_generation and self.context_instruction:
        prompt = final_command_parts[-1]
        full_prompt = self.context_instruction + prompt
        final_command_parts[-1] = full_prompt

    # Args for the CLI
    # Use the final_command_parts as is. Cloud Run service expects [gemini, flags..., prompt]
    gemini_args = final_command_parts

    payload = {
        "args": gemini_args,
        "env": {
            # GEMINI_API_KEY is now mounted as a secret env var on Cloud Run
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

    # Get ID Token for authentication (may be blocking)
    token = await self._get_id_token()

    headers = {"Content-Type": "application/json"}
    if token:
      headers["Authorization"] = f"Bearer {token}"

    try:
      async with aiohttp.ClientSession() as session:
        async with session.post(
            self.service_url, json=payload, headers=headers
        ) as response:
          status_code = response.status
          response_body = await response.text()
    except aiohttp.ClientError as e:
      raise RuntimeError(f"Network error calling Cloud Run: {e}")

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