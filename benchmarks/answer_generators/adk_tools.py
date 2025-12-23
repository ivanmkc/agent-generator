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

"""Tools for the ADK Workflow Agent."""

import os
import subprocess
from pathlib import Path

class AdkTools:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def _resolve_path(self, path_str: str) -> Path:
        """Resolves a path relative to the workspace root and ensures it's safe."""
        # Handle absolute paths that are actually within the workspace
        path = Path(path_str)
        if path.is_absolute():
            try:
                # Try to make it relative to workspace
                path = path.relative_to(self.workspace_root)
            except ValueError:
                 # If it's not relative to workspace, check if it starts with workspace root string
                 if not str(path).startswith(str(self.workspace_root)):
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
        cmd = f"grep -r '{pattern}' '{path}'"
        return self.run_shell_command(cmd)

