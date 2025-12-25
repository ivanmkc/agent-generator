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
import shutil
import tempfile
import unittest
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from benchmarks.answer_generators.adk_tools import AdkTools


class TestAdkTools(unittest.TestCase):
    def setUp(self):
        self.workspace_dir = tempfile.mkdtemp()
        self.workspace_path = Path(self.workspace_dir)
        self.tools = AdkTools(self.workspace_path)

    def tearDown(self):
        shutil.rmtree(self.workspace_dir)

    # --- ReadFileTool Tests ---

    def test_read_file_basic(self):
        filename = "test.txt"
        content = "Hello World"
        self.tools.write_file(filename, content)
        result = self.tools.read_file(filename)
        self.assertEqual(result, content)

    def test_read_file_absolute_path_in_workspace(self):
        filename = "test_abs.txt"
        content = "Absolute"
        full_path = self.workspace_path / filename
        self.tools.write_file(filename, content)
        result = self.tools.read_file(str(full_path))
        self.assertEqual(result, content)

    def test_read_file_not_found(self):
        result = self.tools.read_file("nonexistent.txt")
        self.assertIn("Error: File not found", result)

    def test_read_file_is_directory(self):
        os.makedirs(self.workspace_path / "subdir")
        result = self.tools.read_file("subdir")
        self.assertIn("Error: Path", result)
        self.assertIn("is not a file", result)

    def test_read_file_outside_workspace(self):
        # Create a file outside workspace
        outside_dir = tempfile.mkdtemp()
        try:
            outside_file = Path(outside_dir) / "secret.txt"
            with open(outside_file, "w") as f:
                f.write("secret")
            
            # Try to access it via ..
            # Note: _resolve_path prevents this by resolving canonical paths
            result = self.tools.read_file(f"../{os.path.basename(outside_dir)}/secret.txt")
            self.assertIn("Access denied", result)
            
            # Try absolute path outside
            result_abs = self.tools.read_file(str(outside_file))
            self.assertIn("Access denied", result_abs)
        finally:
            shutil.rmtree(outside_dir)

    def test_read_file_pagination_and_truncation(self):
        filename = "long_lines.txt"
        lines = [f"Line {i}\n" for i in range(10)]
        self.tools.write_file(filename, "".join(lines))

        # 1. Offset only
        result = self.tools.read_file(filename, offset=5)
        self.assertIn("Line 5", result)
        self.assertNotIn("Line 4", result)
        # Should show truncated message because offset > 0
        self.assertIn("IMPORTANT: The file content has been truncated", result)

        # 2. Limit only
        result = self.tools.read_file(filename, limit=3)
        self.assertIn("Line 0", result)
        self.assertIn("Line 2", result)
        self.assertNotIn("Line 3", result)
        self.assertIn("IMPORTANT: The file content has been truncated", result)
        self.assertIn("Showing lines 0-2 of 10", result)

        # 3. Offset + Limit
        result = self.tools.read_file(filename, offset=2, limit=2)
        self.assertIn("Line 2", result)
        self.assertIn("Line 3", result)
        self.assertNotIn("Line 1", result)
        self.assertNotIn("Line 4", result)
        self.assertIn("Showing lines 2-3 of 10", result)

        # 4. Offset beyond end
        result = self.tools.read_file(filename, offset=20)
        self.assertIn("Error: Offset 20 is beyond the end", result)

    def test_read_file_binary(self):
        filename = "binary.bin"
        full_path = self.workspace_path / filename
        # Write invalid utf-8 bytes
        with open(full_path, "wb") as f:
            f.write(b'\x80\x81')
        
        result = self.tools.read_file(filename)
        self.assertIn("Error: File binary.bin appears to be binary", result)

    # --- WriteFileTool Tests ---

    def test_write_file_creates_dirs(self):
        filename = "subdir/deep/nested/test.txt"
        content = "content"
        result = self.tools.write_file(filename, content)
        self.assertIn("Successfully wrote", result)
        self.assertTrue((self.workspace_path / filename).exists())

    def test_write_file_overwrites(self):
        filename = "overwrite.txt"
        self.tools.write_file(filename, "original")
        self.tools.write_file(filename, "new")
        self.assertEqual(self.tools.read_file(filename), "new")

    # --- ListDirectoryTool Tests ---

    def test_list_directory_basic(self):
        self.tools.write_file("a.txt", "")
        self.tools.write_file("b.txt", "")
        os.makedirs(self.workspace_path / "sub")
        
        result = self.tools.list_directory(".")
        self.assertIn("[DIR] sub", result)
        self.assertIn("a.txt", result)
        self.assertIn("b.txt", result)

    def test_list_directory_sorting(self):
        self.tools.write_file("z_file.txt", "")
        os.makedirs(self.workspace_path / "a_dir")
        
        result = self.tools.list_directory(".")
        lines = result.splitlines()
        # Find indices
        dir_idx = next(i for i, line in enumerate(lines) if "a_dir" in line)
        file_idx = next(i for i, line in enumerate(lines) if "z_file.txt" in line)
        
        # Directory should come before file even if 'a' < 'z'
        self.assertLess(dir_idx, file_idx)

    def test_list_directory_empty(self):
        os.makedirs(self.workspace_path / "empty")
        result = self.tools.list_directory("empty")
        self.assertIn("is empty", result)

    def test_list_directory_ignore(self):
        self.tools.write_file("keep.py", "")
        self.tools.write_file("ignore.pyc", "")
        self.tools.write_file("__pycache__/cache", "")
        
        result = self.tools.list_directory(".", ignore=["*.pyc", "__pycache__"])
        self.assertIn("keep.py", result)
        self.assertNotIn("ignore.pyc", result)
        self.assertNotIn("__pycache__", result)

    def test_list_directory_not_found(self):
        result = self.tools.list_directory("nonexistent")
        self.assertIn("Error: Directory not found", result)

    def test_list_directory_is_file(self):
        self.tools.write_file("file.txt", "")
        result = self.tools.list_directory("file.txt")
        self.assertIn("Error: Path", result)
        self.assertIn("is not a directory", result)

    # --- RunShellCommandTool Tests ---

    def test_run_shell_command_basic(self):
        # We can use real echo here since it's standard
        result = self.tools.run_shell_command("echo 'test output'")
        self.assertIn("Command: echo 'test output'", result)
        self.assertIn("Stdout: test output", result)
        self.assertIn("Exit Code: 0", result)

    def test_run_shell_command_cwd(self):
        os.makedirs(self.workspace_path / "subdir")
        result = self.tools.run_shell_command("pwd", dir_path="subdir")
        # The output path might resolve symlinks on Mac, so check end of path
        self.assertIn("subdir", result)
        self.assertIn("Directory: subdir", result)

    def test_run_shell_command_env_var(self):
        # AdkTools copies os.environ, so we can set a var in this process
        key = "TEST_VAR"
        val = "test_val"
        os.environ[key] = val
        try:
            result = self.tools.run_shell_command(f"echo ${key}")
            self.assertIn(f"Stdout: {val}", result)
        finally:
            del os.environ[key]

    def test_run_shell_command_timeout(self):
        # Mock subprocess.run to raise TimeoutExpired
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep", timeout=1)):
            result = self.tools.run_shell_command("sleep 10")
            self.assertIn("Error: Command timed out", result)

    def test_run_shell_command_failure(self):
        result = self.tools.run_shell_command("ls nonexistentfile")
        self.assertIn("Exit Code:", result)
        # Exit code for ls failure is usually 1, or something non-zero
        self.assertNotIn("Exit Code: 0", result)
        self.assertIn("Stderr:", result)

    # --- SearchFilesTool Tests ---
    
    def test_search_files(self):
        self.tools.write_file("a.txt", "findme")
        self.tools.write_file("b.txt", "ignore")
        
        result = self.tools.search_files("findme", ".")
        self.assertIn("a.txt", result)
        self.assertIn("findme", result)

    def test_search_files_quoting(self):
        # Ensure single quotes don't break the command
        self.tools.write_file("quote.txt", "It's a test")
        result = self.tools.search_files("It's", ".")
        self.assertIn("quote.txt", result)

    # --- RunAdkAgentTool Tests ---

    def test_run_adk_agent(self):
        agent_code = "def create_agent(model_name): pass"
        prompt = "test prompt"
        model = "gemini-pro"
        initial_state = {"key": "value"}

        # Mock run_shell_command to verify it gets called with correct python script
        with patch.object(self.tools, "run_shell_command") as mock_run_shell:
            mock_run_shell.return_value = "Agent Output"
            
            result = self.tools.run_adk_agent(agent_code, prompt, model, initial_state=initial_state)
            
            self.assertEqual(result, "Agent Output")
            
            # Check arguments
            mock_run_shell.assert_called_once()
            cmd = mock_run_shell.call_args[0][0]
            self.assertIn("python3", cmd)
            self.assertIn("_adk_runner_", cmd)
            self.assertIn("--agent-file", cmd)
            self.assertIn("--prompt 'test prompt'", cmd)
            self.assertIn(f"--model-name {model}", cmd)
            self.assertIn(f"--initial-state '{json.dumps(initial_state)}'", cmd)

            # Cleanup check
            files = list(self.workspace_path.glob("agent_to_run_*.py"))
            self.assertEqual(len(files), 0)

if __name__ == "__main__":
    unittest.main()
