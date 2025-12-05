import asyncio
import json
import os
import shutil
import subprocess

import pytest


def docker_available():
  return shutil.which("docker") is not None


@pytest.mark.asyncio
@pytest.mark.skipif(not docker_available(), reason="Docker not available")
@pytest.mark.parametrize("server_name", ["context7"])
async def test_mcp_server_running(server_name: str):
  """
  Verifies that the specified MCP server is running and connected
  within the Gemini CLI Docker container by checking the output of 'gemini mcp list'.
  """
  image_name = "gemini-cli-mcp-context7"

  # Ensure real credentials for the Gemini CLI to function
  if not os.environ.get("GEMINI_API_KEY"):
    pytest.skip(
        "GEMINI_API_KEY environment variable not set. Cannot run Gemini CLI"
        " calls."
    )

  # We need to pass the real API key to the docker container
  gemini_api_key = os.environ.get("GEMINI_API_KEY")
  context7_api_key = os.environ.get("CONTEXT7_API_KEY")

  env_vars = []
  if gemini_api_key:
    env_vars.append(f"-e")
    env_vars.append(f"GEMINI_API_KEY={gemini_api_key}")
  if context7_api_key:
    env_vars.append(f"-e")
    env_vars.append(f"CONTEXT7_API_KEY={context7_api_key}")

  # Ask the Gemini CLI to list MCP servers (text output expected)
  cmd = [
      "docker",
      "run",
      "--rm",
      *env_vars,
      image_name,
      "mcp",
      "list",  # No --output-format json
  ]

  proc = await asyncio.create_subprocess_exec(
      *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
  )

  stdout, stderr = await proc.communicate()
  stdout_str = stdout.decode()
  stderr_str = stderr.decode()

  assert proc.returncode == 0, (
      f"Docker command failed with code {proc.returncode}.\nStderr:"
      f" {stderr_str}\nStdout: {stdout_str}"
  )

  print(f"DEBUG: Gemini CLI MCP List Output (text):\n{stdout_str}")

  # Verify 'context7' server and its 'Connected' status in textual output
  assert server_name in stdout_str, (
      f"Server '{server_name}' not found in MCP list"
      f" output.\nOutput:\n{stdout_str}"
  )
  # The output format is: icon serverName ... - Status
  # e.g. "✓ context7 ... - Connected"
  # We check for "Connected" (case sensitive usually, but code says 'Connected')
  assert (
      "Connected" in stdout_str
  ), f"Server '{server_name}' is not Connected. Output:\n{stdout_str}"

  # Verify the tool is present. The output might not list tools by default in 'list' command?
  # The provided code snippet for listCommand doesn't explicitly loop over tools to print them,
  # it prints server status.
  # "serverInfo" includes url/command.
  # It does NOT seem to print the tool list in the provided `list.ts`.
  # So we can only verify connection status.

  # If we want to verify tools, we might need another command or assume connection implies tools are available.
  # For this test, verifying connection is a huge step forward.
