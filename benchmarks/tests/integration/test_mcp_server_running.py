import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from benchmarks.benchmark_candidates import get_gcloud_project
from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import (
    GeminiCliPodmanAnswerGenerator,
    DEFAULT_IMAGE_PREFIX,
)

def container_runtime_available():
  return shutil.which("podman") is not None


@pytest.mark.asyncio
@pytest.mark.skipif(not container_runtime_available(), reason="Container runtime (Podman) not available")
@pytest.mark.parametrize(
    "server_name, service_name, check_command, expected_text",
    [
        ("context7", "mcp-context7", ["mcp", "list"], "context7"),
        ("adk-docs-ext", "adk-docs-ext", ["extensions", "list"], "adk-docs-ext"),
    ],
)
async def test_mcp_server_running(server_name: str, service_name: str, check_command: list[str], expected_text: str, monkeypatch: pytest.MonkeyPatch):
  gemini_api_key = os.environ.get("GEMINI_API_KEY")
  if not gemini_api_key:
    pytest.skip("GEMINI_API_KEY environment variable not set.")
  monkeypatch.setenv("GEMINI_API_KEY", gemini_api_key)

  context7_api_key = os.environ.get("CONTEXT7_API_KEY")
  if server_name == "context7" and not context7_api_key:
      pytest.skip("CONTEXT7_API_KEY environment variable not set for context7 test.")
  elif context7_api_key:
      monkeypatch.setenv("CONTEXT7_API_KEY", context7_api_key)

  project_id = get_gcloud_project()
  monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", project_id)

  """
  Verifies that the specified MCP server or extension is installed/configured
  within the Gemini CLI Podman container.
  """
  # Ensure real credentials for the Gemini CLI to function
  if not os.environ.get("GEMINI_API_KEY"):
    pytest.skip(
        "GEMINI_API_KEY environment variable not set. Cannot run Gemini CLI"
        " calls."
    )

  # Instantiate the generator to handle image building
  generator = GeminiCliPodmanAnswerGenerator(
      dockerfile_dir=Path("."),
      service_name=service_name,
      auto_deploy=True,
      force_deploy=False
  )

  print(f"Setting up generator for {service_name} (building image if needed)...")
  await generator.setup()

  image_name = generator.image_name
  # Use fully qualified name if generator logic implies it
  if ":" not in image_name and service_name != "base":
      image_name = f"{DEFAULT_IMAGE_PREFIX}:{service_name}"

  print(f"Using image: {image_name}")

  # We need to pass the real API key to the podman container
  gemini_api_key = os.environ.get("GEMINI_API_KEY")
  context7_api_key = os.environ.get("CONTEXT7_API_KEY")

  env_vars = []
  if gemini_api_key:
    env_vars.extend(["-e", f"GEMINI_API_KEY={gemini_api_key}"])
  if context7_api_key:
    env_vars.extend(["-e", f"CONTEXT7_API_KEY={context7_api_key}"])

  # Unified config directory for all services
  env_vars.extend(["-e", "GEMINI_CONFIG_DIR=/root/.gemini/"])

  cmd = ["podman", "run", "--rm", *env_vars, image_name, "gemini", *check_command]
  # For adk-docs-ext, we need to handle the case where the command might need to be 'gemini extensions list'
  # The check_command is ["extensions", "list"].
  # The image entrypoint is exec "$@".
  # So "podman run ... image gemini extensions list" is correct.
  
  # For mcp-context7, same: "podman run ... image gemini mcp list".
  
  # However, if the image entrypoint expects just arguments to gemini (e.g. if entrypoint was `gemini "$@"`),
  # then we wouldn't include "gemini".
  # But we verified both entrypoints are `exec "$@"`.
  # And the `gemini` executable must be in path.

  # Special handling if needed:
  # mcp-context7 previously used `npm exec gemini`. Let's see if `gemini` is in PATH.
  # If `gemini-cli-base` puts it in PATH, we are good.
  # Assuming `gemini` is in PATH for now.

  proc = await asyncio.create_subprocess_exec(
      *cmd, stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE
  )
  stdout, stderr = await proc.communicate()
  stdout_str = stdout.decode()
  stderr_str = stderr.decode()

  assert proc.returncode == 0, (
      f"Podman command failed with code {proc.returncode}.\nStderr:"
      f" {stderr_str}\nStdout: {stdout_str}"
  )

  print(f"DEBUG: Gemini CLI Output:\n{stdout_str}")

  assert expected_text in stdout_str, (
      f"Expected text '{expected_text}' not found in output.\nOutput:\n{stdout_str}"
  )
  
  if "extensions" in check_command:
      assert "No extensions installed" not in stdout_str, (
          f"Extension '{expected_text}' failed to install. Output:\n{stdout_str}"
      )
  
  if "mcp" in check_command and "Disconnected" in stdout_str:
      print(f"WARNING: Server '{server_name}' is configured but Disconnected.")
  elif "mcp" in check_command:
      # Optional stricter check if we expect connection
      # assert "Connected" in stdout_str
      pass
