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
from pathlib import Path
from typing import Any

from benchmarks.answer_generators.gemini_cli_answer_generator import (
    GeminiCliAnswerGenerator,
)
from benchmarks.data_models import TraceLogEvent


class GeminiCliPodmanAnswerGenerator(GeminiCliAnswerGenerator):
  """An AnswerGenerator that uses the gemini CLI inside a Podman container."""

  def __init__(
      self,
      image_name: str,
      model_name: str = "gemini-2.5-pro",
      context: str | Path | None = None,
      context_instruction: str | None = None,
  ):
    """Initializes the GeminiCliPodmanAnswerGenerator.

    Args:
      image_name: The name of the Podman image to use. This can be a full
        repository path (e.g., "gcr.io/my-project/my-image:latest") or a
        local image name (e.g., "my-local-image").
      model_name: The name of the Gemini model to use. Defaults to "gemini-2.5-pro".
      context: Optional path to a context file or directory to mount into the
        Podman container.
      context_instruction: Optional instruction to prepend to the user prompt.
    """
    super().__init__(model_name=model_name, context=context, cli_path="gemini")
    self.image_name = image_name
    self.context_instruction = context_instruction

  @property
  def name(self) -> str:
    """Returns a unique name for this generator instance."""
    base = super().name
    return (
        f"GeminiCliPodmanAnswerGenerator({self.model_name},"
        f" image={self.image_name})"
    )

  async def _run_cli_command(
      self, prompt: str
  ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
    """Executes the gemini CLI command inside Podman and returns the parsed JSON output."""

    full_prompt = prompt
    if self.context_instruction:
      full_prompt = self.context_instruction + prompt

    # Prepare Podman command
    # We need to run the container, pass auth env vars, and execute the gemini command.

    podman_args = ["podman", "run", "--rm"]

    # Handle Authentication
    # 1. Check for GEMINI_API_KEY
    if os.environ.get("GEMINI_API_KEY"):
      podman_args.extend(["-e", "GEMINI_API_KEY"])

    # Pass CONTEXT7_API_KEY if present (for MCP)
    if os.environ.get("CONTEXT7_API_KEY"):
      podman_args.extend(["-e", "CONTEXT7_API_KEY"])

    # 2. Check for Vertex AI params
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
      podman_args.extend(["-e", "GOOGLE_GENAI_USE_VERTEXAI"])
      if os.environ.get("GOOGLE_API_KEY"):
        podman_args.extend(["-e", "GOOGLE_API_KEY"])
      if os.environ.get("GOOGLE_CLOUD_PROJECT"):
        podman_args.extend(["-e", "GOOGLE_CLOUD_PROJECT"])
      if os.environ.get("GOOGLE_CLOUD_LOCATION"):
        podman_args.extend(["-e", "GOOGLE_CLOUD_LOCATION"])

      # Handle ADC file mapping
      adc_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
      if adc_path:
        # We must mount the file into the container
        # Use a fixed path inside the container to avoid path issues
        container_adc_path = "/tmp/google_credentials.json"
        podman_args.extend(["-v", f"{adc_path}:{container_adc_path}"])
        podman_args.extend(
            ["-e", f"GOOGLE_APPLICATION_CREDENTIALS={container_adc_path}"]
        )

    # Podman Image
    podman_args.append(self.image_name)

    # Gemini Command (inside container)
    # Note: we use the same arguments as the base class, but 'gemini' is the entrypoint or command
    gemini_args = [
        self.cli_path,  # "gemini"
        full_prompt,
        "--output-format",
        "stream-json",  # Enabled output-format stream-json for better tracing
        "--model",
        self.model_name,
        "--yolo",
        # "--sandbox",  <-- Removed because we are already in a container
    ]

    # Construct the full command arguments
    cmd_args = podman_args + gemini_args

    # Create subprocess
    proc = await asyncio.create_subprocess_exec(
        *cmd_args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    stdout_str = stdout.decode()
    stderr_str = stderr.decode()

    logs: list[TraceLogEvent] = []

    # Process stderr as a raw log event if present
    if stderr_str:
      logs.append(
          TraceLogEvent(
              type="PODMAN_CLI_STDERR", source="podman", content=stderr_str
          )
      )

    if proc.returncode != 0:
      error_msg = stderr_str.strip() or stdout_str.strip()
      raise RuntimeError(
          f"Gemini CLI (Podman) failed with code {proc.returncode}: {error_msg}"
      )

    # Parse NDJSON events to reconstruct the response object and detailed logs
    response_dict = {"response": ""}

    for line in stdout_str.splitlines():
      line = line.strip()
      if not line:
        continue
      try:
        event = json.loads(line)
        event_type = event.get("type")
        timestamp = event.get("timestamp")

        # Handle potential 'data' wrapper if present (though usually flat in CLI)
        event_data = event.get("data", event)

        # Create a structured TraceLogEvent
        log_event = TraceLogEvent(
            type=event_type or "unknown",
            source="podman",
            timestamp=timestamp,
            details=event,  # Store full raw event in details
        )

        if event_type == "init":
          log_event.type = "system_init"
          log_event.content = event

        elif event_type == "message":
          role = event_data.get("role")
          log_event.role = role
          content = event_data.get("content")
          log_event.content = content

          if role in ["model", "assistant"]:
            # Aggregate model response for the final output
            if isinstance(content, list):
              for part in content:
                if isinstance(part, dict) and "text" in part:
                  response_dict["response"] += part["text"]
            elif isinstance(content, str):
              response_dict["response"] += content

        elif event_type == "tool_use":
          log_event.tool_name = event_data.get("tool_name")
          log_event.tool_call_id = event_data.get("tool_id")
          log_event.tool_input = event_data.get("parameters")

        elif event_type == "tool_result":
          log_event.tool_call_id = event_data.get("tool_id")
          log_event.tool_output = str(event_data.get("output"))

        elif event_type == "result":
          log_event.type = "system_result"
          if "stats" in event_data:
            response_dict["stats"] = event_data["stats"]
            log_event.content = event_data["stats"]

        logs.append(log_event)

      except json.JSONDecodeError:
        # Fallback for non-JSON lines
        logs.append(
            TraceLogEvent(
                type="PODMAN_CLI_STDOUT_RAW", source="podman", content=line
            )
        )

    return response_dict, logs
