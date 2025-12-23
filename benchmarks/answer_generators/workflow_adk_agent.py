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

"""An AnswerGenerator that uses a workflow-based ADK Agent with tools."""

import os
import subprocess
from pathlib import Path
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager

# --- Tool Definitions ---

def read_file(path: str) -> str:
    """Reads the content of a file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {path}: {e}"

def write_file(path: str, content: str) -> str:
    """Writes content to a file."""
    try:
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file {path}: {e}"

def list_directory(path: str = ".") -> str:
    """Lists files in a directory."""
    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return f"Error listing directory {path}: {e}"

def run_shell_command(command: str) -> str:
    """Runs a shell command and returns stdout/stderr."""
    try:
        # Security Note: In a real environment, this is dangerous.
        # For benchmarking in a controlled container, it allows the agent to run tests.
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return f"Stdout:\n{result.stdout}\nStderr:\n{result.stderr}\nReturn Code: {result.returncode}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as e:
        return f"Error running command: {e}"

def search_files(pattern: str, path: str = ".") -> str:
    """Searches for files matching a pattern using grep."""
    return run_shell_command(f"grep -r '{pattern}' '{path}'")


class WorkflowAdkAnswerGenerator(AdkAnswerGenerator):
    """
    An AnswerGenerator that uses a tool-enabled ADK Agent to solve benchmarks.
    This agent mimics the capabilities of a CLI agent but runs entirely within the ADK.
    """

    def __init__(
        self,
        model_name: str = "gemini-2.5-pro",
        api_key_manager: ApiKeyManager | None = None,
    ):
        # Define the tools
        tools = [
            FunctionTool(read_file),
            FunctionTool(write_file),
            FunctionTool(list_directory),
            FunctionTool(run_shell_command),
            FunctionTool(search_files),
        ]

        # Define the agent with a robust system instruction
        agent = LlmAgent(
            name="workflow_solver",
            model=model_name,
            tools=tools,
            instruction=(
                "You are an expert software engineer tasked with solving programming benchmarks. "
                "You have access to a set of tools to read code, write files, and run commands. "
                "\n\n"
                "**Workflow:**\n"
                "1.  **Analyze:** Read the benchmark requirements and explore the codebase if necessary."
                "2.  **Plan:** Determine what code needs to be written or fixed."
                "3.  **Implement:** Use `write_file` to create or modify the necessary Python files."
                "4.  **Verify:** Use `run_shell_command` to execute tests (e.g., `pytest`) or run the code directly to ensure it works."
                "5.  **Iterate:** If verification fails, analyze the error, fix the code, and verify again."
                "6.  **Final Output:** Once satisfied, output the final JSON as requested by the user prompt."
            ),
        )

        super().__init__(agent=agent, name=f"WorkflowAdk({model_name})")
        self.api_key_manager = api_key_manager
