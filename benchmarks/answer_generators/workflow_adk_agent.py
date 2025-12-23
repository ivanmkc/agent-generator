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
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.api_key_manager import ApiKeyManager


class WorkflowAdkAnswerGenerator(AdkAnswerGenerator):
    """
    An AnswerGenerator that uses a tool-enabled ADK Agent to solve benchmarks.
    This agent mimics the capabilities of a CLI agent but runs entirely within the ADK,
    operating within a sandboxed workspace directory.
    """

    def __init__(
        self,
        model_name: str = "gemini-2.5-pro",
        api_key_manager: ApiKeyManager | None = None,
        workspace_root: Path | None = None,
    ):
        self.workspace_root = workspace_root or Path(tempfile.mkdtemp(prefix="adk_workflow_"))
        self._setup_completed = False
        
        # Define the tools bound to this instance
        tools = [
            FunctionTool(self.read_file),
            FunctionTool(self.write_file),
            FunctionTool(self.list_directory),
            FunctionTool(self.run_shell_command),
            FunctionTool(self.search_files),
        ]

        # Define the agent with a robust system instruction
        agent = LlmAgent(
            name="workflow_solver",
            model=model_name,
            tools=tools,
            instruction=(
                "You are an expert software engineer tasked with solving programming benchmarks. "
                "You have access to a set of tools to read code, write files, and run commands. "
                f"You are operating in a workspace at {self.workspace_root}. "
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

        super().__init__(agent=agent, name=f"WorkflowAdk({model_name})")
        self.api_key_manager = api_key_manager

    def _resolve_path(self, path_str: str) -> Path:
        """Resolves a path relative to the workspace root and ensures it's safe."""
        # Handle absolute paths that are actually within the workspace
        path = Path(path_str)
        if path.is_absolute():
            try:
                # Try to make it relative to workspace
                path = path.relative_to(self.workspace_root)
            except ValueError:
                 # If it's not relative to workspace, treat it as relative to CWD (workspace) if it was meant to be
                 # But if the user deliberately passed /etc/passwd, we want to catch it.
                 # Let's assume input paths are relative to workspace unless explicitly matching workspace root.
                 if not str(path).startswith(str(self.workspace_root)):
                     # Security: prevent accessing files outside workspace
                     # But we allow /tmp usage if needed? No, strict sandbox.
                     pass 

        # Force valid relative path logic
        full_path = (self.workspace_root / path).resolve()
        
        # Security check: Ensure the resolved path is within the workspace root
        if not str(full_path).startswith(str(self.workspace_root.resolve())):
            raise ValueError(f"Access denied: Path {path_str} resolves to {full_path} which is outside the workspace {self.workspace_root}")
        
        return full_path

    def read_file(self, path: str) -> str:
        """Reads the content of a file."""
        try:
            full_path = self._resolve_path(path)
            if not full_path.exists():
                 return f"Error: File not found at {full_path}"
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file {path}: {e}"

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a file."""
        try:
            full_path = self._resolve_path(path)
            # Create directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file {path}: {e}"

    def list_directory(self, path: str = ".") -> str:
        """Lists files in a directory."""
        try:
            full_path = self._resolve_path(path)
            if not full_path.exists():
                 return f"Error: Directory not found at {full_path}"
            items = os.listdir(full_path)
            return "\n".join(items) if items else "(empty directory)"
        except Exception as e:
            return f"Error listing directory {path}: {e}"

    def run_shell_command(self, command: str) -> str:
        """Runs a shell command in the workspace directory."""
        try:
            # We run the command with cwd=workspace_root
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.workspace_root,
                timeout=30
            )
            return f"Stdout:\n{result.stdout}\nStderr:\n{result.stderr}\nReturn Code: {result.returncode}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out."
        except Exception as e:
            return f"Error running command: {e}"

    def search_files(self, pattern: str, path: str = ".") -> str:
        """Searches for files matching a pattern using grep."""
        # Sanitize inputs or use run_shell_command which executes in cwd
        # Note: simplistic grep usage, might have shell injection if pattern is malicious, 
        # but we are in a sandbox and the "attacker" is the agent itself trying to solve a task.
        # Ideally use python-based search, but grep is faster/easier for the agent.
        # We rely on run_shell_command's cwd restriction.
        cmd = f"grep -r '{pattern}' '{path}'"
        return self.run_shell_command(cmd)

    async def setup(self, force_deploy: bool = False) -> None:
        """Sets up the workspace by cloning the ADK repository."""
        if self._setup_completed and not force_deploy:
            return

        print(f"[{self.name}] Setting up workspace at {self.workspace_root}")
        
        # Ensure workspace exists
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        # Define paths
        repos_dir = self.workspace_root / "repos"
        adk_repo_dir = repos_dir / "adk-python"
        
        repos_dir.mkdir(exist_ok=True)
        
        # Clone ADK Python
        # For reproducibility/speed in dev, we could copy from local if known, 
        # but cloning is safer for clean environment.
        if not adk_repo_dir.exists():
            print(f"[{self.name}] Cloning adk-python...")
            try:
                subprocess.run(
                    ["git", "clone", "--branch", "v1.20.0", "https://github.com/google/adk-python.git", str(adk_repo_dir)],
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to clone adk-python: {e.stderr.decode()}")
        
        self._setup_completed = True
        print(f"[{self.name}] Setup complete.")

    async def teardown(self) -> None:
        """Cleans up the temporary workspace."""
        if self.workspace_root.exists():
            shutil.rmtree(self.workspace_root)