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

"""An AnswerGenerator that uses the gemini CLI inside a Docker container."""

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from benchmarks.answer_generators.gemini_cli_answer_generator import (
    GeminiCliAnswerGenerator,
)
from benchmarks.data_models import TraceLogEvent


class GeminiCliDockerAnswerGenerator(GeminiCliAnswerGenerator):
  """An AnswerGenerator that uses the gemini CLI inside a Docker container."""

  def __init__(
      self,
      image_name: str,
      model_name: str = "gemini-2.5-pro",
      context: str | Path | None = None,
      context_instruction: str | None = None,
  ):
    """Initializes the GeminiCliDockerAnswerGenerator.

    Args:
      image_name: The name of the Docker image to use. This can be a full
        repository path (e.g., "gcr.io/my-project/my-image:latest") or a
        local image name (e.g., "my-local-image").
      model_name: The name of the Gemini model to use. Defaults to "gemini-2.5-pro".
      context: Optional path to a context file or directory to mount into the
        Docker container.
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
        f"GeminiCliDockerAnswerGenerator({self.model_name},"
        f" image={self.image_name})"
    )

  async def run_cli_command(
      self, command_parts: list[str]
  ) -> tuple[dict[str, Any], list[TraceLogEvent]]:
    """Executes the gemini CLI command inside Docker and returns the parsed JSON output."""

    # Extract prompt from the last argument (convention from base class)
    # If the command doesn't have a prompt (e.g. 'mcp list'), we don't modify it.
    
    # Heuristic: If the last arg is a long string or looks like a prompt, we treat it as such.
    # Commands like 'mcp list' won't have a prompt.
    # The base class constructs command_parts as [cli_path, flags..., prompt].
    
    # We check if we are running a 'generate' command (implied by presence of --model etc)
    # vs a tool command (mcp list).
    is_generation = "--model" in command_parts
    
    final_command_parts = list(command_parts)

    if is_generation and self.context_instruction:
        prompt = final_command_parts[-1]
        full_prompt = self.context_instruction + prompt
        final_command_parts[-1] = full_prompt

    # Create a temporary directory on the host to capture logs
    host_tmp_dir = tempfile.mkdtemp()

    try:
        # Prepare Docker command
        # We need to run the container, pass auth env vars, and execute the gemini command.

        docker_args = ["docker", "run", "--rm"]
        
        # Mount the host temp dir to /tmp in the container to capture error logs
        docker_args.extend(["-v", f"{host_tmp_dir}:/tmp"])

        # Handle Authentication
        # 1. Check for GEMINI_API_KEY
        if os.environ.get("GEMINI_API_KEY"):
          docker_args.extend(["-e", "GEMINI_API_KEY"])

        # Pass CONTEXT7_API_KEY if present (for MCP)
        if os.environ.get("CONTEXT7_API_KEY"):
          docker_args.extend(["-e", "CONTEXT7_API_KEY"])

        # 2. Check for Vertex AI params
        if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
          docker_args.extend(["-e", "GOOGLE_GENAI_USE_VERTEXAI"])
          if os.environ.get("GOOGLE_API_KEY"):
            docker_args.extend(["-e", "GOOGLE_API_KEY"])
          if os.environ.get("GOOGLE_CLOUD_PROJECT"):
            docker_args.extend(["-e", "GOOGLE_CLOUD_PROJECT"])
          if os.environ.get("GOOGLE_CLOUD_LOCATION"):
            docker_args.extend(["-e", "GOOGLE_CLOUD_LOCATION"])

          # Handle ADC file mapping
          adc_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
          if adc_path:
            # We must mount the file into the container
            # Use a fixed path inside the container to avoid path issues
            container_adc_path = "/tmp/google_credentials.json"
            docker_args.extend(["-v", f"{adc_path}:{container_adc_path}"])
            docker_args.extend(
                ["-e", f"GOOGLE_APPLICATION_CREDENTIALS={container_adc_path}"]
            )

        # Docker Image
        docker_args.append(self.image_name)

        # Gemini Command (inside container)
        # Use the final_command_parts passed from the base class
        # But ensure the executable matches what we expect inside the container?
        # self.cli_path is 'gemini'. If base passed 'gemini', it should be fine.
        
        gemini_args = final_command_parts

        # Construct the full command arguments
        cmd_args = docker_args + gemini_args

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
                  type="DOCKER_CLI_STDERR", source="docker", content=stderr_str
              )
          )

        if proc.returncode != 0:
          error_msg = stderr_str.strip() or stdout_str.strip()
          
          # Check for detailed error logs in the mounted temp dir
          detailed_logs = ""
          try:
              for file_name in os.listdir(host_tmp_dir):
                  if file_name.startswith("gemini-client-error"):
                      file_path = os.path.join(host_tmp_dir, file_name)
                      with open(file_path, "r") as f:
                          content = f.read()
                          detailed_logs += f"\n--- {file_name} ---\n{content}\n"
          except Exception as e:
              detailed_logs += f"\n(Failed to read detailed error logs: {e})"

          if detailed_logs:
              error_msg += f"\n\nDetailed In-Container Error Logs:{detailed_logs}"

          raise RuntimeError(
              f"Gemini CLI (Docker) failed with code {proc.returncode}: {error_msg}"
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
                source="docker",
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
                    type="DOCKER_CLI_STDOUT_RAW", source="docker", content=line
                )
            )

        return response_dict, logs

    finally:
        # Cleanup temporary directory
        shutil.rmtree(host_tmp_dir, ignore_errors=True)
