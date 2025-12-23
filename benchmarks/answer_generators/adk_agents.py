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

"""Candidate ADK Agents for benchmarking."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from benchmarks.answer_generators.adk_tools import AdkTools
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager


def create_default_adk_agent(model_name: str = "gemini-2.5-pro") -> LlmAgent:
    """Creates the default LlmAgent used for ADK benchmarking."""
    return LlmAgent(
        name="adk_test_agent",
        model=model_name,
        instruction=(
            "You are a senior engineer specializing in the ADK Python framework."
            " Your task is to answer questions or fix code with expert precision."
            " Always respond with a JSON object conforming to the specified"
            " schema, enclosed in a markdown code block (```json...```)."
        ),
    )


def create_workflow_agent(workspace_root: Path, model_name: str = "gemini-2.5-pro") -> LlmAgent:
    """
    Creates a workflow-enabled LlmAgent with file system and shell tools.
    
    Args:
        workspace_root: The root directory for the agent's workspace.
        model_name: The Gemini model to use.
    """
    tools_helper = AdkTools(workspace_root)
    
    tools = [
        FunctionTool(tools_helper.read_file),
        FunctionTool(tools_helper.write_file),
        FunctionTool(tools_helper.list_directory),
        FunctionTool(tools_helper.run_shell_command),
        FunctionTool(tools_helper.search_files),
    ]

    return LlmAgent(
        name="workflow_solver",
        model=model_name,
        tools=tools,
        instruction=(
            "You are an expert software engineer tasked with solving programming benchmarks. "
            "You have access to a set of tools to read code, write files, and run commands. "
            f"You are operating in a workspace at {workspace_root}. "
            "The ADK Python repository is available at `repos/adk-python` relative to the workspace root. "
            "\n\n"
            "**Workflow:**\n"
            "1.  **Analyze:** Read the benchmark requirements and explore the codebase if necessary. "
            "Use `list_directory` and `read_file` to understand the environment.\n"
            "2.  **Plan:** Determine what code needs to be written or fixed.\n"
            "3.  **Implement:** Use `write_file` to create or modify the necessary Python files.\n"
            "4.  **Verify:** Use `run_shell_command` to execute tests (e.g., `pytest`) or run the code directly to ensure it works.\n"
            "5.  **Iterate:** If verification fails, analyze the error, fix the code, and verify again.\n"
            "6.  **Final Output:** Once satisfied, output the final JSON as requested by the user prompt."
        ),
    )

def create_workflow_adk_generator(
    model_name: str,
    api_key_manager: ApiKeyManager | None = None
) -> AdkAnswerGenerator:
    """
    Factory to create an AdkAnswerGenerator with a fully managed workflow agent.
    Handles workspace creation, agent instantiation, and lifecycle hooks.
    """
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_workflow_"))
    agent = create_workflow_agent(workspace_root, model_name)
    
    async def setup_hook():
        print(f"[WorkflowAdk] Setting up workspace at {workspace_root}")
        workspace_root.mkdir(parents=True, exist_ok=True)
        repos_dir = workspace_root / "repos"
        adk_repo_dir = repos_dir / "adk-python"
        repos_dir.mkdir(exist_ok=True)
        
        if not adk_repo_dir.exists():
            print(f"[WorkflowAdk] Cloning adk-python...")
            try:
                subprocess.run(
                    ["git", "clone", "--branch", "v1.20.0", "https://github.com/google/adk-python.git", str(adk_repo_dir)],
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to clone adk-python: {e.stderr.decode()}")
        print(f"[WorkflowAdk] Setup complete.")

    async def teardown_hook():
        if workspace_root.exists() and "adk_workflow_" in str(workspace_root):
            shutil.rmtree(workspace_root)

    return AdkAnswerGenerator(
        agent=agent,
        name=f"WorkflowAdk({model_name})",
        setup_hook=setup_hook,
        teardown_hook=teardown_hook,
        api_key_manager=api_key_manager
    )
