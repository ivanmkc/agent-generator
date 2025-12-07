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

"""An AnswerGenerator that uses the gemini CLI inside a Podman container."""

import asyncio
import json
import os
import subprocess
import re
from pathlib import Path
from typing import Any, Optional

from benchmarks.answer_generators.gemini_cli_answer_generator import \
    GeminiCliAnswerGenerator
from benchmarks.data_models import TraceLogEvent
from benchmarks.utils import parse_cli_stream_json_output


# Define known images and their build configurations
IMAGE_DEFINITIONS = {
    "base": {
        "source_dir": "base",
        "dockerfile": "base/Dockerfile",
        "dependencies": [],
        "build_args": {},
    },
    "gemini-cli-base": {
        "source_dir": "base",
        "dockerfile": "base/Dockerfile",
        "dependencies": [],
        "build_args": {},
    },
    "adk-python": {
        "source_dir": "adk-python",
        "dockerfile": "adk-python/Dockerfile",
        "dependencies": ["base"],
        "build_args": {"BASE_IMAGE": "adk-gemini-sandbox:base"},
    },
    "mcp-context7": {
        "source_dir": "gemini-cli-mcp-context7",
        "dockerfile": "gemini-cli-mcp-context7/Dockerfile",
        "dependencies": ["base"],
        "build_args": {"BASE_IMAGE": "adk-gemini-sandbox:base"},
    },
    "adk-docs-ext": {
        "source_dir": "adk-docs-ext",
        "dockerfile": "adk-docs-ext/Dockerfile",
        "dependencies": ["base"],
        "build_args": {"BASE_IMAGE": "adk-gemini-sandbox:base"},
    },
}

DEFAULT_IMAGE_PREFIX = "adk-gemini-sandbox"


class GeminiCliPodmanAnswerGenerator(GeminiCliAnswerGenerator):
  """An AnswerGenerator that uses the gemini CLI inside a Podman container."""

  def __init__(  # pylint: disable=super-init-not-called
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
  ):
    """Initializes the GeminiCliPodmanAnswerGenerator.

    Matches the API of GeminiCliCloudRunAnswerGenerator for interchangeability.

    Args:
      dockerfile_dir: Path to the directory containing the Dockerfile.
        Used if building a custom image. If using a managed image (e.g. adk-python),
        this can be any path (even dummy) if auto_deploy is False or image is managed.
      service_name: Used as the default image name (or alias).
      model_name: The name of the Gemini model to use.
      project_id: Ignored (compatibility).
      region: Ignored (compatibility).
      context_instruction: Instruction to prepend to the user prompt.
      auto_deploy: Whether to automatically build the image.
      image_name: The Podman image name. If None, derived from service_name.
      force_deploy: If True, rebuilds the image even if it exists.
    """
    super().__init__(model_name=model_name, cli_path="gemini")
    
    # Determine the effective image key (e.g., "adk-python" from "adk-gemini-sandbox:adk-python")
    effective_image_key = image_name.split(":")[-1] if image_name and ":" in image_name else (image_name or service_name)

    # Always store the fully qualified local image name
    if effective_image_key in IMAGE_DEFINITIONS or image_name and image_name.startswith(f"{DEFAULT_IMAGE_PREFIX}:"):
        self.image_name = image_name if image_name and image_name.startswith(f"{DEFAULT_IMAGE_PREFIX}:") else f"{DEFAULT_IMAGE_PREFIX}:{effective_image_key}"
    else:
        # For unmanaged or custom images, use the provided name directly
        self.image_name = image_name or service_name

    self.dockerfile_dir = Path(dockerfile_dir)
    self.context_instruction = context_instruction
    self.auto_deploy = auto_deploy
    self.force_deploy = force_deploy
    self._image_checked = False

  @property
  def name(self) -> str:
    """Returns a unique name for this generator instance."""
    return (
        f"GeminiCliPodmanAnswerGenerator({self.model_name},"
        f" image={self.image_name})"
    )

  async def setup(self) -> None:
    """Ensures the Podman image is built and ready."""
    await self._ensure_image_ready()

  async def _ensure_image_ready(self):
    """Checks if the requested image exists and builds it if necessary."""
    if self._image_checked and not self.force_deploy:
      return
      
    # Determine if this is a managed image
    image_tag = self.image_name
    if ":" in image_tag:
      # e.g. adk-gemini-sandbox:adk-python -> adk-python
      image_key = image_tag.split(":")[-1]
    else:
      image_key = image_tag

    # 1. Check if it's a known managed image
    if image_key in IMAGE_DEFINITIONS:
      if self.auto_deploy or self.force_deploy:
         await self._build_image_chain(image_key, force=self.force_deploy)
         
      self._image_checked = True
      # Reset force_deploy after first check to avoid rebuilding on every call if object is reused
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
        # Check if image exists
        proc = await asyncio.create_subprocess_exec(
            "podman", "image", "exists", full_image_name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        
        if proc.returncode == 0:
            return # Already exists

    print(f"Building Custom Podman image: {full_image_name} from {self.dockerfile_dir}...")
    
    build_cmd = [
        "podman", "build",
        "-t", full_image_name,
        str(self.dockerfile_dir)
    ]
    
    # If a Dockerfile exists explicitly in the dir, use it (otherwise defaults to Dockerfile)
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
    definition = IMAGE_DEFINITIONS[image_key]
    
    # 1. Build dependencies first
    for dep_key in definition["dependencies"]:
      # Propagate force to dependencies
      await self._build_image_chain(dep_key, force=force)

    # 2. Check if current image exists
    full_image_name = f"{DEFAULT_IMAGE_PREFIX}:{image_key}"
    
    if not force:
        # Check if image exists
        proc = await asyncio.create_subprocess_exec(
            "podman", "image", "exists", full_image_name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        
        if proc.returncode == 0:
          return

    # 3. Build the image
    print(f"Building Podman image: {full_image_name}...")
    
    base_path = Path(__file__).parent
    source_path = base_path / definition["source_dir"]
    dockerfile_path = base_path / definition["dockerfile"]
    
    build_cmd = [
        "podman", "build",
        "-t", full_image_name,
        "-f", str(dockerfile_path),
    ]
    
    for arg_name, arg_val in definition["build_args"].items():
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

  # Override _run_cli_command from parent to handle Podman-specific execution
  async def _run_cli_command(
      self, cli_args: list[str], direct_command_parts: Optional[list[str]] = None
  ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
    """Executes the gemini CLI command inside Podman and returns the parsed output and raw logs."""
    # Ensure image is ready before running
    await self._ensure_image_ready()

    # Prepare Podman command
    podman_args = ["podman", "run", "--rm"]

    # Handle Authentication (env vars)
    if os.environ.get("GEMINI_API_KEY"):
      podman_args.extend(["-e", "GEMINI_API_KEY"])
    if os.environ.get("CONTEXT7_API_KEY"):
      podman_args.extend(["-e", "CONTEXT7_API_KEY"])
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
      podman_args.extend(["-e", "GOOGLE_GENAI_USE_VERTEXAI"])
      if os.environ.get("GOOGLE_API_KEY"):
        podman_args.extend(["-e", "GOOGLE_API_KEY"])
      if os.environ.get("GOOGLE_CLOUD_PROJECT"):
        podman_args.extend(["-e", "GOOGLE_CLOUD_PROJECT"])
      if os.environ.get("GOOGLE_CLOUD_LOCATION"):
        podman_args.extend(["-e", "GOOGLE_CLOUD_LOCATION"])

    adc_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if adc_path:
      container_adc_path = "/tmp/google_credentials.json"
      podman_args.extend(["-v", f"{adc_path}:{container_adc_path}"])
      podman_args.extend(
          ["-e", f"GOOGLE_APPLICATION_CREDENTIALS={container_adc_path}"]
      )
    
    # Explicitly set GEMINI_CONFIG_DIR for the container
    podman_args.extend(["-e", "GEMINI_CONFIG_DIR=/root/.gemini/"])

    # Podman Image
    podman_args.append(self.image_name)

    # Full command to execute inside the container
    # The cli_path (gemini) and cli_args are passed as direct arguments to the container.
    if direct_command_parts:
        full_command = [self.cli_path] + direct_command_parts
    else:
        full_command = [self.cli_path] + cli_args

    # Create subprocess
    proc = await asyncio.create_subprocess_exec(
        *podman_args, *full_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    stdout_str = stdout.decode()
    stderr_str = stderr.decode()

    # Initialize logs with stderr content first
    logs: list[TraceLogEvent] = []
    for line in stderr_str.splitlines():
        if line.strip():
            logs.append(TraceLogEvent(type="CLI_STDERR", source="podman", content=line.strip()))

    # Parse stdout. If stream-json, parse events. Otherwise, treat as raw message.
    response_dict = {"stdout": stdout_str, "stderr": stderr_str, "exit_code": proc.returncode, "response": ""}
    if "--output-format" in cli_args and "stream-json" in cli_args:
        parsed_response_dict, parsed_logs = parse_cli_stream_json_output(stdout_str)
        response_dict.update(parsed_response_dict)
        logs.extend(parsed_logs)
    else:
        # If not stream-json, treat stdout as a single response message for logging purposes
        if stdout_str.strip():
            logs.append(TraceLogEvent(type="CLI_STDOUT_RAW", source="podman", content=stdout_str.strip()))
        response_dict["response"] = stdout_str.strip()  # Direct text response

    if proc.returncode != 0:
      error_msg = stderr_str.strip() or stdout_str.strip()
      raise RuntimeError(
          f"Gemini CLI failed with code {proc.returncode}: {error_msg}"
      )

    return response_dict, logs