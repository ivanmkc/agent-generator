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

"""An AnswerGenerator that uses the gemini CLI hosted in a local Podman container."""

import asyncio
import atexit
import json
import os
import shutil
import subprocess
import tempfile
import re
import uuid
import socket
import time
from pathlib import Path
from typing import Any, Optional

import aiohttp

from benchmarks.answer_generators.gemini_cli_answer_generator import \
    GeminiCliAnswerGenerator
from benchmarks.data_models import TraceLogEvent
from benchmarks.utils import parse_cli_stream_json_output
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import (
    ImageDefinition,
    IMAGE_DEFINITIONS,
    DEFAULT_IMAGE_PREFIX,
)

class GeminiCliPodmanAnswerGenerator(GeminiCliAnswerGenerator):
  """An AnswerGenerator that uses the gemini CLI hosted in a local Podman container (API Server mode)."""

  def __init__(  # pylint: disable=super-init-not-called
      self,
      dockerfile_dir: str | Path,
      image_name: str,
      model_name: str = "gemini-2.5-pro",
      context_instruction: str | None = None,
      auto_deploy: bool = False,
      force_deploy: bool = False,
      # Injected dependencies
      image_definitions: dict[str, ImageDefinition] = IMAGE_DEFINITIONS,
      default_image_prefix: str = DEFAULT_IMAGE_PREFIX,
  ):
    """Initializes the GeminiCliPodmanAnswerGenerator.

    Matches the API of GeminiCliCloudRunAnswerGenerator for interchangeability.
    """
    super().__init__(model_name=model_name, cli_path="gemini")
    
    # Determine the effective image key
    effective_image_key = image_name.split(":")[-1] if ":" in image_name else image_name

    # Always store the fully qualified local image name
    if effective_image_key in image_definitions or image_name.startswith(f"{default_image_prefix}:"):
        self.image_name = image_name if image_name.startswith(f"{default_image_prefix}:") else f"{default_image_prefix}:{effective_image_key}"
    else:
        self.image_name = image_name
    self._image_definitions = image_definitions
    self._default_image_prefix = default_image_prefix

    self.dockerfile_dir = Path(dockerfile_dir)
    self.context_instruction = context_instruction
    self.auto_deploy = auto_deploy
    self.force_deploy = force_deploy
    self._image_checked = False
    self._setup_completed = False
    self._setup_lock: asyncio.Lock | None = None
    
    # Server state
    self._container_name = f"gemini-cli-server-{uuid.uuid4().hex[:8]}"
    self._port: int | None = None
    self._base_url: str | None = None

  @property
  def name(self) -> str:
    """Returns a unique name for this generator instance."""
    return (
        f"GeminiCliPodmanAnswerGenerator({self.model_name},"
        f" image={self.image_name})"
    )

  async def setup(self) -> None:
    """Ensures the Podman image is built and starts the API server container."""
    if self._setup_lock is None:
        self._setup_lock = asyncio.Lock()
        
    async with self._setup_lock:
        if self._setup_completed:
            return

        print(f"[Podman Setup] Starting setup for {self.name}")
        await self._ensure_image_ready()
        
        # Ensure any previous container is cleaned up before starting a new one
        self._cleanup_server_container()
        
        await self._start_server_container()
        self._setup_completed = True
        print(f"[Podman Setup] Setup for {self.name} completed. Listening on {self._base_url}")

  async def _ensure_image_ready(self):
    """Checks if the requested image exists and builds it if necessary."""
    print(f"[Podman Ensure Image] Checking image readiness for {self.image_name}")
    if self._image_checked and not self.force_deploy:
      return
      
    image_tag = self.image_name
    image_key = image_tag.split(":")[-1] if ":" in image_tag else image_tag

    # 1. Check if it's a known managed image
    if image_key in self._image_definitions:
      if self.auto_deploy or self.force_deploy:
         await self._build_image_chain(image_key, force=self.force_deploy)
      self._image_checked = True
      self.force_deploy = False 
      return
      
    # 2. If not managed, check if we have a dockerfile_dir to build from
    if (self.auto_deploy or self.force_deploy) and self.dockerfile_dir and self.dockerfile_dir.exists():
        await self._build_custom_image(force=self.force_deploy)
        self._image_checked = True
        self.force_deploy = False
        return

    # 3. Otherwise, just check existence (assume pre-built)
    self._image_checked = True
    
  async def _build_custom_image(self, force: bool = False):
    """Builds an image from self.dockerfile_dir."""
    full_image_name = self.image_name
    
    if not force:
        proc = await asyncio.create_subprocess_exec(
            "podman", "image", "exists", full_image_name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        if proc.returncode == 0:
            return

    print(f"Building Custom Podman image: {full_image_name} from {self.dockerfile_dir}...")
    
    build_cmd = ["podman", "build", "-t", full_image_name, str(self.dockerfile_dir)]
    if (self.dockerfile_dir / "Dockerfile").exists():
         build_cmd.extend(["-f", str(self.dockerfile_dir / "Dockerfile")])

    build_proc = await asyncio.create_subprocess_exec(
        *build_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await build_proc.communicate()
    
    if build_proc.returncode != 0:
        error_msg = stderr.decode().strip() or stdout.decode().strip()
        raise RuntimeError(f"Failed to build custom image {full_image_name}: {error_msg}")
        
    print(f"Successfully built {full_image_name}")

  async def _build_image_chain(self, image_key: str, force: bool = False):
    """Recursively builds dependencies and then the target image."""
    definition = self._image_definitions[image_key]
    for dep_key in definition.dependencies:
      await self._build_image_chain(dep_key, force=force)

    full_image_name = f"{self._default_image_prefix}:{image_key}"
    
    if not force:
        proc = await asyncio.create_subprocess_exec(
            "podman", "image", "exists", full_image_name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        if proc.returncode == 0:
          return

    print(f"Building Podman image: {full_image_name}...")
    
    base_path = Path(__file__).parent
    source_path = base_path / definition.source_dir
    dockerfile_path = base_path / definition.dockerfile
    
    build_cmd = [
        "podman", "build", "-t", full_image_name, "-f", str(dockerfile_path),
    ]
    for arg_name, arg_val in definition.build_args.items():
        build_cmd.extend(["--build-arg", f"{arg_name}={arg_val}"])
        
    build_cmd.append(str(source_path))

    build_proc = await asyncio.create_subprocess_exec(
        *build_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await build_proc.communicate()
    
    if build_proc.returncode != 0:
        error_msg = stderr.decode().strip() or stdout.decode().strip()
        raise RuntimeError(f"Failed to build image {full_image_name}: {error_msg}")
        
    print(f"Successfully built {full_image_name}")

  async def _start_server_container(self):
      """Starts the container in daemon mode exposing the API server."""
      # 1. Find a free port
      sock = socket.socket()
      sock.bind(("", 0))
      self._port = sock.getsockname()[1]
      sock.close()
      
      self._base_url = f"http://localhost:{self._port}"
      
      # 2. Register cleanup
      atexit.register(self._cleanup_server_container)
      
      print(f"[Podman Setup] Starting server container: {self._container_name} on port {self._port}")
      
      podman_args = [
          "podman", "run", "-d", "--rm", 
          "--name", self._container_name,
          "-p", f"{self._port}:8080"
      ]
      
      # Pass Env Vars
      for env_var in ["GEMINI_API_KEY", "CONTEXT7_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI", 
                      "GOOGLE_API_KEY", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"]:
          if os.environ.get(env_var):
              podman_args.extend(["-e", env_var])

      # ADC Credentials
      adc_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
      if adc_path:
        # We need to mount the creds file
        # And tell the container where it is
        container_adc_path = "/tmp/google_credentials.json"
        podman_args.extend(["-v", f"{adc_path}:{container_adc_path}"])
        podman_args.extend(
            ["-e", f"GOOGLE_APPLICATION_CREDENTIALS={container_adc_path}"]
        )
      
      # Config Dir
      podman_args.extend(["-e", "GEMINI_CONFIG_DIR=/tmp/.gemini/"])

      podman_args.append(self.image_name)
      # Explicitly run the server, which works for both CMD-only images (overrides CMD)
      # and ENTRYPOINT images (passed as args to entrypoint script)
      podman_args.extend(["python3", "/usr/local/bin/cli_server.py"])
      
      proc = await asyncio.create_subprocess_exec(
          *podman_args,
          stdout=asyncio.subprocess.PIPE,
          stderr=asyncio.subprocess.PIPE,
          stdin=asyncio.subprocess.DEVNULL
      )
      stdout, stderr = await proc.communicate()
      
      if proc.returncode != 0:
          error_msg = stderr.decode().strip() or stdout.decode().strip()
          raise RuntimeError(f"Failed to start server container: {error_msg}")

      # 3. Wait for Health Check
      print("[Podman Setup] Waiting for server health check...")
      max_retries = 20
      for i in range(max_retries):
          try:
              async with aiohttp.ClientSession() as session:
                  # Functional Health Check: Try to actually run the CLI
                  # Must start with 'gemini' to pass server validation
                  payload = {"args": [self.cli_path, "--version"]}
                  async with session.post(self._base_url, json=payload, timeout=2.0) as resp:
                      if resp.status == 200:
                          data = await resp.json()
                          # Support both keys just in case, but server sends 'returncode'
                          exit_code = data.get("returncode", data.get("exit_code"))
                          if exit_code == 0:
                              print("[Podman Setup] Server ready (Functional Check Passed).")
                              return
                          else:
                              print(f"[Podman Setup] Health check failed: {data}")
                      else:
                           print(f"[Podman Setup] Health check HTTP error: {resp.status}")
          except Exception:
              pass
          await asyncio.sleep(0.5)
      
      # If we get here, it failed. Try to get logs.
      logs = ""
      try:
          log_proc = await asyncio.create_subprocess_exec(
              "podman", "logs", self._container_name,
              stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
          )
          l_out, l_err = await log_proc.communicate()
          logs = (l_out + l_err).decode()
      except Exception:
          logs = "Could not retrieve logs."
          
      self._cleanup_server_container()
      raise RuntimeError(f"Server container failed to start healthy. Logs:\n{logs}")

  def _cleanup_server_container(self):
      """Stops the persistent container."""
      if not self._container_name:
          return
      try:
          subprocess.run(
              ["podman", "kill", self._container_name],
              stdout=subprocess.DEVNULL, 
              stderr=subprocess.DEVNULL,
              timeout=5
          )
      except Exception:
          pass

  async def _run_cli_command(
      self,
      cli_args: list[str],
      direct_command_parts: Optional[list[str]] = None
  ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
    """Executes the gemini CLI command via the local API server."""
    if not self._setup_completed:
      await self.setup()

    # Construct args list for server
    # Server expects ["gemini", "arg1", ...]
    # cli_args are ["--flag", ...]
    # direct_command_parts are ["subcmd", ...]
    
    full_args = [self.cli_path] # "gemini"
    if direct_command_parts:
        full_args.extend(direct_command_parts)
    else:
        full_args.extend(cli_args)

    payload = {
        "args": full_args,
        "env": {
            # Pass extra envs if needed per request, but we mostly did it at startup
        }
    }

    logs: list[TraceLogEvent] = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(self._base_url, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"API Server returned {response.status}: {text}")
                
                result = await response.json()
    except Exception as e:
        # Mark setup as incomplete so next retry attempts to restart the container
        self._setup_completed = False
        raise RuntimeError(f"Failed to communicate with Podman API server: {e}")

    stdout_str = result.get("stdout", "")
    stderr_str = result.get("stderr", "")
    returncode = result.get("returncode", 0)

    # Initialize logs with stderr content
    for line in stderr_str.splitlines():
        if line.strip():
            logs.append(TraceLogEvent(type="CLI_STDERR", source="podman_server", content=line.strip()))

    response_dict = {"stdout": stdout_str, "stderr": stderr_str, "exit_code": returncode, "response": ""}
    
    # Parse stdout
    if "--output-format" in cli_args and "stream-json" in cli_args:
        parsed_response_dict, parsed_logs = parse_cli_stream_json_output(stdout_str)
        response_dict.update(parsed_response_dict)
        logs.extend(parsed_logs)
    else:
        if stdout_str.strip():
            logs.append(TraceLogEvent(type="CLI_STDOUT_RAW", source="podman_server", content=stdout_str.strip()))
        response_dict["response"] = stdout_str.strip()

    if returncode != 0:
        error_msg = stderr_str.strip() or stdout_str.strip()
        raise RuntimeError(f"Gemini CLI failed with code {returncode}: {error_msg}")

    return response_dict, logs
