# Copyright 2025 Google LLC

# %%
# Parameters cell for papermill
run_output_dir_str = "benchmark_runs/default_output" # This will be overwritten by papermill
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

"""
Defines standard candidate AnswerGenerators for benchmarking.
This file serves as a central registry of configured generators to ensure consistency
across different evaluation runs.
"""

from enum import StrEnum
import os
from pathlib import Path
import subprocess

from benchmarks.answer_generators.adk_agents import create_default_adk_agent
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.answer_generators.gemini_answer_generator import GeminiAnswerGenerator
from benchmarks.answer_generators.gemini_cli_local_answer_generator import (
    GeminiCliLocalAnswerGenerator,
)
from benchmarks.answer_generators.gemini_cli_docker import (
    GeminiCliDockerAnswerGenerator,
    GeminiCliCloudRunAnswerGenerator,
    GeminiCliPodmanAnswerGenerator,
    IMAGE_DEFINITIONS
)
from benchmarks.answer_generators.ground_truth_answer_generator import (
    GroundTruthAnswerGenerator,
)
from benchmarks.answer_generators.trivial_answer_generator import TrivialAnswerGenerator
from benchmarks.utils import permute

# Define model constants as enum
class ModelName(StrEnum):
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_3_0_PRO = "gemini-3.0-pro"


# Helper to get project ID for Docker image
def get_gcloud_project():
  try:
    if os.environ.get("GOOGLE_CLOUD_PROJECT"):
      return os.environ.get("GOOGLE_CLOUD_PROJECT")
    # Fallback to gcloud config
    return subprocess.check_output(
        ["gcloud", "config", "get-value", "project"], text=True
    ).strip()
  except (subprocess.CalledProcessError, FileNotFoundError):
    # Fallback hardcoded if everything fails (user can modify this)
    return "ivanmkc-experimental-665175"


project_id = get_gcloud_project()


# Create pre-configured agent instances for AdkAnswerGenerator
agent_flash = create_default_adk_agent(model_name=ModelName.GEMINI_2_5_FLASH)
agent_pro = create_default_adk_agent(model_name=ModelName.GEMINI_2_5_PRO)

# List of standard candidate generators
CANDIDATE_GENERATORS = [
      GeminiCliPodmanAnswerGenerator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        dockerfile_dir=Path(
            "benchmarks/answer_generators/gemini_cli_docker/base"
        ),
        image_name="gemini-cli:base",
        image_definitions=IMAGE_DEFINITIONS,
    ),
    GeminiCliPodmanAnswerGenerator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        dockerfile_dir=Path(
            "benchmarks/answer_generators/gemini_cli_docker/adk-python"
        ),
        image_name="gemini-cli:adk-python",
        image_definitions=IMAGE_DEFINITIONS,
    ),
    # # Gemini CLI Cloud Run Generator (ADK Docs Extension)
    # GeminiCliCloudRunAnswerGenerator(
    #     model_name=ModelName.GEMINI_2_5_FLASH,
    #     dockerfile_dir=Path(
    #         "benchmarks/answer_generators/gemini_cli_docker/adk-docs-ext"
    #     ),
    #     service_name="adk-docs-ext",
    #     project_id=project_id,
    #     auto_deploy=True,
    # ),
    # # Gemini CLI Cloud Run Generator (Standalone Base - for baseline comparison)
    # GeminiCliCloudRunAnswerGenerator(
    #     model_name=ModelName.GEMINI_2_5_FLASH,
    #     dockerfile_dir=Path(
    #         "benchmarks/answer_generators/gemini_cli_docker/base"
    #     ),
    #     service_name="gemini-cli-base",
    #     project_id=project_id,
    #     auto_deploy=True, # Auto-deploy the base image
    # ),
    # Gemini CLI Docker Generator (Standard)
    # GeminiCliDockerAnswerGenerator(
    #     model_name=ModelName.GEMINI_2_5_FLASH,
    #     image_name=f"gcr.io/{project_id}/gemini-cli-base:latest",
    #     context_instruction=ADK_REPO_INSTRUCTION,
    # ),
    # GeminiCliDockerAnswerGenerator(
    #     model_name=ModelName.GEMINI_2_5_FLASH,
    #     image_name=f"gcr.io/{project_id}/gemini-cli:adk-python",
    #     context_instruction=ADK_REPO_INSTRUCTION,
    # ),
    # # Gemini CLI Docker Generator (MCP Context7)
    # GeminiCliDockerAnswerGenerator(
    #     model_name=ModelName.GEMINI_2_5_FLASH,
    #     image_name="gemini-cli-mcp-context7",
    # ),
    # Direct Gemini SDK generators (Baselines)
    # *permute(
    #     GeminiAnswerGenerator,
    #     model_name=[ModelName.GEMINI_2_5_FLASH],
    #     context=[None, Path("llms-relevant.txt")]
    # ),
    # # Gemini CLI generators
    # GeminiCliLocalAnswerGenerator(model_name=ModelName.GEMINI_2_5_FLASH),
    # Control generators
    GroundTruthAnswerGenerator(),
    TrivialAnswerGenerator(),
]
