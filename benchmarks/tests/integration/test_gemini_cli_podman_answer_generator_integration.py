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

import os
from pathlib import Path
import subprocess
from typing import Optional

from pydantic import BaseModel
import pytest

from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import (
    GeminiCliPodmanAnswerGenerator,
)
from benchmarks.data_models import MultipleChoiceBenchmarkCase
from benchmarks.data_models import TraceLogEvent
from benchmarks.tests.integration.predefined_cases import ADK_QUESTION_DOCKER_CASE


PODMAN_IMAGE = "adk-gemini-sandbox:adk-python"


def podman_available():
  try:
    subprocess.run(
        ["podman", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return True
  except (FileNotFoundError, subprocess.CalledProcessError):
    return False


@pytest.mark.parametrize("case", [ADK_QUESTION_DOCKER_CASE])
@pytest.mark.asyncio
@pytest.mark.skipif(not podman_available(), reason="Podman not available")
async def test_podman_generator_integration_adk_question(
    tmp_path, case: MultipleChoiceBenchmarkCase
):
  """
  Runs a real integration test asking a question about the ADK codebase using Podman.
  Verifies that the model uses tools to inspect the code.
  """

  # Ensure we have credentials to pass
  if not os.environ.get("GEMINI_API_KEY") and not os.environ.get(
      "GOOGLE_GENAI_USE_VERTEXAI"
  ):
    pytest.skip(
        "No API credentials (GEMINI_API_KEY or VERTEX AI vars) found in"
        " environment."
    )

  # Inject context instruction to guide the model to the repo
  repo_instruction = (
      "\nCONTEXT: You are working in a Podman container. The current working"
      " directory is `/repos`. The project source code is located in the"
      " subdirectory `./adk-python`. You MUST look into `./adk-python` to find"
      " source files, tests, or configuration.\n\n"
  )

  generator = GeminiCliPodmanAnswerGenerator(
      dockerfile_dir=tmp_path,
      service_name="adk-python",
      model_name="gemini-2.5-flash",
      image_name=PODMAN_IMAGE,
      context_instruction=repo_instruction,
      auto_deploy=True,
  )

  try:
    result = await generator.generate_answer(case)

    assert (
        result.output.answer == "B"
    ), f"Expected B, got {result.output.answer}"

    # Check for evidence of tool use (e.g., listing directory or reading file)
    # The specific tool name might vary, but it should be present in the logs.
    # Common tools: list_directory, read_file, search_file_content, codebase_investigator
    tool_used = False
    for log_entry in result.trace_logs:
      if log_entry.type == "tool_use":
        if any(
            tool in log_entry.tool_name
            for tool in [
                "list_directory",
                "read_file",
                "glob",
                "codebase_investigator",
                "search_file_content",
            ]
        ):
          tool_used = True
          break

    assert tool_used, (
        "Expected tool usage"
        " (list_directory/read_file/glob/codebase_investigator/search_file_content) in logs. Logs"
        f" preview:\n{result.trace_logs[:500]}"
    )
  except RuntimeError as e:
    # If the image is missing, we might get a specific error.
    if "Unable to find image" in str(e) or "pull access denied" in str(e):
      pytest.fail(
          f"Could not pull/find Podman image {PODMAN_IMAGE}. Please ensure it"
          f" is built/pushed.\nError: {e}"
      )
    else:
      pytest.fail(f"Podman execution failed: {e}")
