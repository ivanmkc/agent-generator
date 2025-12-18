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

from benchmarks.api_key_manager import API_KEY_MANAGER, ApiKeyManager, KeyType
from benchmarks.answer_generators.gemini_cli_answer_generator import \
    GeminiCliAnswerGenerator
from benchmarks.data_models import TraceLogEvent
from benchmarks.utils import parse_cli_stream_json_output
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import (
    ImageDefinition,
    IMAGE_DEFINITIONS,
    IMAGE_PREFIX,
)
from benchmarks.answer_generators.hash_utils import calculate_source_hash

class GeminiCliPodmanAnswerGenerator(GeminiCliAnswerGenerator):
  """An AnswerGenerator that uses the gemini CLI hosted in a local Podman container (API Server mode)."""

  def __init__(
      self,
      dockerfile_dir: str | Path,
      image_name: str,
      image_definitions: dict[str, ImageDefinition],
      model_name: str = "gemini-2.5-pro",
      context_instruction: str | None = None,
      service_url: str | None = None,
      api_key_manager: ApiKeyManager | None = None,
  ):
    # Store all arguments specific to this class
    self.image_name = image_name
    self._image_definitions = image_definitions
    self.dockerfile_dir = Path(dockerfile_dir)
    self.context_instruction = context_instruction

    # Call the parent constructor with only the arguments it expects
    super().__init__(model_name=model_name, cli_path="gemini", context=self.context_instruction, api_key_manager=api_key_manager)
    
    self._image_checked = False
    
    # Server state
    self._port: int | None = None
    
    if service_url:
        self._base_url = service_url
        self._is_proxy = True
        self._container_name = None
        # We enforce calling setup() to verify the proxy
        self._setup_completed = False 
    else:
        self._base_url = None
        self._is_proxy = False
        self._container_name = f"gemini-cli-server-{uuid.uuid4().hex[:8]}"
        self._setup_completed = False
        
    self._setup_lock = asyncio.Lock()

  @property
  def name(self) -> str:
    """Returns a unique name for this generator instance."""
    return (
        f"GeminiCliPodmanAnswerGenerator({self.model_name},"
        f" image={self.image_name})"
    )

  async def setup(self, force_deploy: bool = False) -> None:
    """Ensures the Podman image is built and starts the API server container."""
    async with self._setup_lock:
        if self._setup_completed and not self._is_proxy:
            return

        if self._is_proxy:
            self._setup_completed = True
            return

        print(f"[Podman Setup] Starting setup for {self.name}")
        await self._ensure_image_ready(force=force_deploy)
        
        # Ensure any stale container with the same name is removed before starting
        self._cleanup_server_container()
        
        await self._start_server_container()
        self._setup_completed = True
        print(f"[Podman Setup] Setup for {self.name} completed. Listening on {self._base_url}")

  async def teardown(self) -> None:
      """Stops the persistent container."""
      if self._is_proxy:
          return
      self._cleanup_server_container()

  async def _ensure_image_ready(self, force: bool = False):
    """Checks if the requested image exists and builds it if necessary."""
    print(f"[Podman Ensure Image] Checking image readiness for {self.image_name}")
    if self._image_checked and not force:
      return

    # 1. Check if it's a known managed image
    if self.image_name in self._image_definitions:
         await self._build_image_chain(self.image_name, force=force)
         self._image_checked = True
         return
    
    # If we get here, the image is not a known managed image.
    raise RuntimeError(
        f"Image '{self.image_name}' is not a known managed image and no "
        "dockerfile_dir was provided for a custom build."
    )

  async def _get_image_label(self, image_name: str, label_key: str) -> str | None:
      """Retrieves a label value from a Podman image."""
      try:
          print(f"[Podman Build] Inspecting label {label_key} for {image_name}...")
          inspect_cmd = ["podman", "inspect", "--format", f"{{{{.Config.Labels.{label_key}}}}}", image_name]
          print(f"[Podman Build] Running command: {" ".join(inspect_cmd)}")
          proc = await asyncio.create_subprocess_exec(
              *inspect_cmd,
              stdout=asyncio.subprocess.PIPE,
              stderr=asyncio.subprocess.PIPE
          )
          stdout, stderr = await proc.communicate()
          if proc.returncode == 0:
              val = stdout.decode().strip()
              print(f"[Podman Build] Inspect label {label_key} result: {val}")
              return val if val != "<no value>" else None
          else:
             print(f"[Podman Build] Inspect failed: {stderr.decode().strip()}")
      except Exception as e:
          print(f"[Podman Build] Inspect exception: {e}")
          pass
      return None

  async def _execute_podman_build(
      self,
      image_name: str,
      dockerfile_path: Path,
      context_path: Path,
      build_args: Optional[dict[str, str]] = None,
      labels: Optional[dict[str, str]] = None,
  ):
    """Executes the podman build command."""
    print(f"Building Podman image: {image_name} from {context_path} (Dockerfile: {dockerfile_path.name})...")
    
    build_cmd = [
        "podman", "build", "-t", image_name,
        "-f", str(dockerfile_path),
    ]
    
    if build_args:
        for arg_name, arg_val in build_args.items():
            build_cmd.extend(["--build-arg", f"{arg_name}={arg_val}"])
            
    if labels:
        for k, v in labels.items():
            build_cmd.extend(["--label", f"{k}={v}"])

    build_cmd.append(str(context_path))

    print(f"[Podman Build] Running command: {" ".join(build_cmd)}")
    # Use a subprocess directly connected to stdout/stderr to stream output
    import sys
    import time

    start_time = time.monotonic()
    
    build_proc = await asyncio.create_subprocess_exec(
        *build_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    async def read_stream(stream, callback):
        while True:
            line = await stream.readline()
            if not line:
                break
            await callback(line.decode().rstrip())

    async def log_stdout(line):
        print(f"[{image_name}] {line}")
        
    async def log_stderr(line):
        print(f"[{image_name}] {line}", file=sys.stderr)

    # Run readers concurrently
    await asyncio.gather(
        read_stream(build_proc.stdout, log_stdout),
        read_stream(build_proc.stderr, log_stderr)
    )
    
    returncode = await build_proc.wait()
    end_time = time.monotonic()
    duration = end_time - start_time
    
    if returncode != 0:
        raise RuntimeError(f"Failed to build image {image_name}. Exit code: {returncode} (took {duration:.2f}s)")
        
    print(f"Successfully built {image_name} in {duration:.2f}s")
    
  async def _build_image_chain(self, image_key: str, force: bool = False):
    """Recursively builds dependencies and then the target image."""
    definition = self._image_definitions[image_key]
    for dep_key in definition.dependencies:
      await self._build_image_chain(dep_key, force=force)

    full_image_name = image_key
    
    base_path = Path(__file__).parent
    source_path = base_path / definition.source_dir
    dockerfile_path = base_path / definition.dockerfile

    # Calculate local source hash
    print(f"[Podman Build] Calculating source hash for {full_image_name}...")
    current_hash = calculate_source_hash(source_path)
    
    should_build = force
    
    if not should_build:
        print(f"[Podman Build] Checking if image {full_image_name} exists...")
        # Check if image exists
        exists_cmd = ["podman", "image", "exists", full_image_name]
        print(f"[Podman Build] Running command: {" ".join(exists_cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *exists_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            print(f"[Podman Build] Image {full_image_name} not found (rc={proc.returncode}). Build required. Stderr: {stderr.decode().strip()}")
            should_build = True
        else:
            print(f"[Podman Build] Image {full_image_name} found. Checking source hash...")
            # Check hash label
            existing_hash = await self._get_image_label(full_image_name, "source_hash")
            if existing_hash != current_hash:
                print(f"[Podman Build] Source change detected for {full_image_name} (old: {existing_hash}, new: {current_hash}). Rebuilding.")
                should_build = True
            else:
                print(f"[Podman Build] Image {full_image_name} is up to date (hash: {current_hash}).")

    if should_build:
        await self._execute_podman_build(
            image_name=full_image_name,
            dockerfile_path=dockerfile_path,
            context_path=source_path,
            build_args=definition.build_args,
            labels={"source_hash": current_hash}
        )

  async def _start_server_container(self):
      """Starts the container in daemon mode exposing the API server."""
      # 1. Find a free port
      sock = socket.socket()
      sock.bind(("", 0))
      self._port = sock.getsockname()[1]
      sock.close()
      
      self._base_url = f"http://localhost:{self._port}"
      
      # 2. Register cleanup
      # atexit.register(self._cleanup_server_container)
      
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
      # podman_args.extend(["-e", "GEMINI_CONFIG_DIR=/tmp/.gemini/"])

      podman_args.append(self.image_name)
      # Explicitly run the server, which works for both CMD-only images (overrides CMD)
      # and ENTRYPOINT images (passed as args to entrypoint script)
      podman_args.extend(["python3", "/usr/local/bin/cli_server.py"])
      
      print(f"[Podman Setup] Running command: {" ".join(podman_args)}")
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
          
    #   self._cleanup_server_container()
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

  async def run_cli_command(
      self,
      command_parts: list[str],
  ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
    """Executes the gemini CLI command via the local API server."""
    if not self._setup_completed:
      await self.setup()

    # The server expects ["gemini", "arg1", ...]
    # command_parts already contains [self.cli_path, flags..., prompt]
    # self.cli_path is usually "gemini"
    if not self._setup_completed:
      await self.setup()

    full_args = list(command_parts)
    
    # Handle context instruction if needed (Podman supports it via context_instruction attr)
    # Similar to Docker generator logic
    is_generation = "--model" in full_args
    if is_generation and self.context_instruction:
        prompt = full_args[-1]
        full_prompt = self.context_instruction + prompt
        full_args[-1] = full_prompt

    payload = {
        "args": full_args,
        "env": {
            # Pass extra envs if needed per request, but we mostly did it at startup
        }
    }

    # Inject rotated API key if available
    api_key = self.api_key_manager.get_next_key(KeyType.GEMINI_API)
    if api_key:
        payload["env"]["GEMINI_API_KEY"] = api_key

    logs: list[TraceLogEvent] = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(self._base_url, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"API Server returned {response.status}: {text}")
                
                result = await response.json()
    except Exception as e:
        raise RuntimeError(f"Failed to communicate with Podman API server: {e}")

    stdout_str = result.get("stdout", "")
    stderr_str = result.get("stderr", "")
    returncode = result.get("returncode", 0)

    # Initialize logs with stderr content
    for line in stderr_str.splitlines():
        if line.strip():
            logs.append(TraceLogEvent(type="CLI_STDERR", source="podman_server", content=line.strip()))

    # Always log full stdout for debugging/archival
    if stdout_str:
        logs.append(TraceLogEvent(type="CLI_STDOUT_FULL", source="podman_server", content=stdout_str))

    response_dict = {"stdout": stdout_str, "stderr": stderr_str, "exit_code": returncode, "response": ""}
    
    # Parse stdout
    if "--output-format" in full_args and "stream-json" in full_args:
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