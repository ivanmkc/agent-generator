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


def create_workflow_agent(workspace_root: Path, model_name: str = "gemini-2.5-pro", venv_path: Path | None = None) -> LlmAgent:
    """
    Creates a workflow-enabled LlmAgent with file system and shell tools.
    
    Args:
        workspace_root: The root directory for the agent's workspace.
        model_name: The Gemini model to use.
        venv_path: Optional path to a virtual environment to use for shell commands.
    """
    tools_helper = AdkTools(workspace_root, venv_path=venv_path)
    
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
            "A virtual environment is active for your shell commands, with `adk` and `pytest` installed. "
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
    Handles workspace creation, venv setup, agent instantiation, and lifecycle hooks.
    """
    workspace_root = Path(tempfile.mkdtemp(prefix="adk_workflow_"))
    venv_path = workspace_root / "venv"
    
    # Deferred agent creation is not supported by AdkAnswerGenerator __init__ pattern I implemented earlier
    # wait, AdkAnswerGenerator takes an 'agent' instance.
    # So I must create the agent HERE.
    agent = create_workflow_agent(workspace_root, model_name, venv_path=venv_path)
    
    async def setup_hook():
        print(f"[WorkflowAdk] Setting up workspace at {workspace_root}")
        workspace_root.mkdir(parents=True, exist_ok=True)
        repos_dir = workspace_root / "repos"
        adk_repo_dir = repos_dir / "adk-python"
        repos_dir.mkdir(exist_ok=True)
        
        # 1. Clone ADK Python
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
        
        # 2. Create Virtual Environment
        if not venv_path.exists():
            print(f"[WorkflowAdk] Creating virtual environment at {venv_path}...")
            subprocess.run([os.sys.executable, "-m", "venv", str(venv_path)], check=True)
            
            # Helper to run pip in venv
            pip_cmd = [str(venv_path / "bin" / "pip"), "install"]
            
            # 3. Install Dependencies
            print(f"[WorkflowAdk] Installing dependencies...")
            subprocess.run(pip_cmd + ["--upgrade", "pip"], check=True)
            subprocess.run(pip_cmd + ["pytest", "--index-url", "https://pypi.org/simple"], check=True) # Install pytest from PyPI
            
            # 4. Install Cloned Repo (Editable mode)
            # We install the cloned adk-python to allow the agent to test modifications to it if needed, 
            # or just to have it available as a library.
            # Assuming adk-python root has setup.py or pyproject.toml
            print(f"[WorkflowAdk] Installing local adk-python...")
            subprocess.run(pip_cmd + ["-e", str(adk_repo_dir), "--index-url", "https://pypi.org/simple"], check=True)

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
