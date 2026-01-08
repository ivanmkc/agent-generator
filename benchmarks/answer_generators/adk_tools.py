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
import fnmatch
import shlex
import uuid
from pathlib import Path
from typing import List, Optional, Any
import json # Moved to top
import asyncio # Added for async operations
import functools # Added for partial in async operations

class AdkTools:
    def __init__(self, workspace_root: Path, venv_path: Path | None = None):
        self.workspace_root = workspace_root
        self.venv_path = venv_path

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

    def read_file(self, file_path: str, offset: int = 0, limit: int = 1000) -> str:
        """
        Reads and returns the content of a specified file.
        
        If the file is large, the content can be paginated using `offset` and `limit`.
        If truncation occurs (due to `limit`), the output will contain a status message
        and instructions on how to read the next chunk.

        Args:
            file_path: The path to the file to read, relative to the workspace root.
            offset: The 0-based line number to start reading from. Defaults to 0.
            limit: Maximum number of lines to read. If -1, reads the rest of the file (up to a hard limit of 2000). Defaults to 1000.

        Returns:
            The content of the file, or a formatted string containing a truncation message and partial content.
            Returns an error message string starting with "Error:" if the file cannot be read.

        Example:
            >>> read_file("src/main.py", limit=50)
            # Returns the first 50 lines of src/main.py.
            
            >>> read_file("src/main.py", offset=50, limit=50)
            # Returns lines 50-99 of src/main.py.
        """
        try:
            full_path = self._resolve_path(file_path)
            if not full_path.exists():
                 return f"Error: File not found at {full_path}"
            
            if not full_path.is_file():
                return f"Error: Path {full_path} is not a file."

            # TODO: Handle binary files if needed, currently assuming text/utf-8
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                return f"Error: File {file_path} appears to be binary or not UTF-8 encoded."

            total_lines = len(lines)
            
            if offset < 0:
                offset = 0
            
            if offset >= total_lines and total_lines > 0:
                return f"Error: Offset {offset} is beyond the end of the file (total lines: {total_lines})."
            
            MAX_HARD_LIMIT = 2000
            if limit == -1 or limit > MAX_HARD_LIMIT:
                limit = MAX_HARD_LIMIT
            
            end_index = min(offset + limit, total_lines)
            
            selected_lines = lines[offset:end_index]
            
            # Line width truncation
            MAX_LINE_WIDTH = 1000
            processed_lines = []
            lines_width_truncated = False
            
            for line in selected_lines:
                if len(line) > MAX_LINE_WIDTH:
                    processed_lines.append(line[:MAX_LINE_WIDTH] + "... [line truncated]\n")
                    lines_width_truncated = True
                else:
                    processed_lines.append(line)
            
            content = "".join(processed_lines)

            # Check for truncation (count or width)
            lines_count_truncated = (end_index < total_lines) or (offset > 0)
            is_truncated = lines_count_truncated or lines_width_truncated
            
            if is_truncated:
                next_offset = end_index
                msg = f"IMPORTANT: The file content has been truncated (showing {len(selected_lines)} lines).\n"
                if lines_count_truncated:
                    msg += f"Status: Showing lines {offset}-{end_index - 1} of {total_lines} total lines.\n"
                if lines_width_truncated:
                    msg += f"Status: Some lines exceeded {MAX_LINE_WIDTH} characters and were shortened.\n"
                
                msg += f"Action: To read more of the file, you can use the 'offset' and 'limit' parameters in a subsequent 'read_file' call. For example, to read the next section of the file, use offset: {next_offset}.\n"
                msg += f"\n--- FILE CONTENT (truncated) ---\n{content}"
                return msg
            else:
                return content

        except Exception as e:
            return f"Error reading file {file_path}: {e}"

    def replace_text(self, file_path: str, old_string: str, new_string: str, expected_replacements: Optional[int] = None) -> str:
        """
        Replaces text within a file.
        
        This tool requires providing significant context around the change to ensure precise targeting.
        
        Args:
            file_path: The path to the file to modify, relative to the workspace root.
            old_string: The exact literal text to replace.
            new_string: The exact literal text to replace `old_string` with.
            expected_replacements: Optional. Number of replacements expected. Defaults to 1 if not specified.

        Returns:
            Success message or error.
        """
        try:
            full_path = self._resolve_path(file_path)
            if not full_path.exists():
                 return f"Error: File not found at {full_path}"
            
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            count = content.count(old_string)
            
            if count == 0:
                return f"Error: `old_string` not found in file. Ensure exact match including whitespace. Use `read_file` to verify."
            
            expected = expected_replacements if expected_replacements is not None else 1
            
            if count != expected:
                return f"Error: Expected {expected} occurrences of `old_string`, but found {count}. Please specify correct `expected_replacements` or refine `old_string` to be unique."
            
            new_content = content.replace(old_string, new_string)
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            return f"Successfully replaced {count} occurrence(s) in {file_path}."

        except Exception as e:
            return f"Error replacing text in {file_path}: {e}"

    def write_file(self, file_path: str, content: str) -> str:
        """
        Writes content to a specified file.
        
        Creates directories in the path if they do not exist. Overwrites existing files.

        Args:
            file_path: The path to the file to write, relative to the workspace root.
            content: The string content to write to the file.

        Returns:
            A success message starting with "Successfully wrote to...", or an error message starting with "Error:".

        Example:
            >>> write_file("tests/test_foo.py", "def test_foo(): pass")
        """
        try:
            full_path = self._resolve_path(file_path)
            # Create directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file {file_path}: {e}"

    def list_directory(self, dir_path: str, ignore: Optional[List[str]] = None) -> str:
        """
        Lists files and subdirectories within a specified directory.
        
        Can filter out entries using glob patterns provided in `ignore`.

        Args:
            dir_path: The path to the directory to list, relative to the workspace root.
            ignore: A list of glob patterns to ignore (e.g., ['*.pyc', '__pycache__', '.git']).

        Returns:
            A formatted string listing the directory contents. Directories are prefixed with "[DIR] ".
            Returns an error message if the directory does not exist or is inaccessible.

        Example:
            >>> list_directory("src", ignore=["__pycache__"])
            # Returns:
            # Directory listing for src:
            # [DIR] utils
            # main.py
        """
        try:
            full_path = self._resolve_path(dir_path)
            if not full_path.exists():
                 return f"Error: Directory not found at {full_path}"
            if not full_path.is_dir():
                return f"Error: Path {full_path} is not a directory."

            entries = []
            try:
                with os.scandir(full_path) as it:
                    for entry in it:
                        # Check ignore patterns
                        if ignore:
                            should_ignore = False
                            for pattern in ignore:
                                if fnmatch.fnmatch(entry.name, pattern):
                                    should_ignore = True
                                    break
                            if should_ignore:
                                continue

                        is_dir = entry.is_dir()
                        entries.append({
                            "name": entry.name,
                            "is_dir": is_dir,
                            "path": entry.path
                        })
            except OSError as e:
                 return f"Error listing directory {dir_path}: {e}"

            if not entries:
                return f"Directory {dir_path} is empty."

            # Sort: directories first, then alphabetical
            entries.sort(key=lambda x: (not x["is_dir"], x["name"]))

            output_lines = []
            output_lines.append(f"Directory listing for {dir_path}:")
            for entry in entries:
                prefix = "[DIR] " if entry["is_dir"] else ""
                output_lines.append(f"{prefix}{entry['name']}")

            return "\n".join(output_lines)

        except Exception as e:
            return f"Error listing directory {dir_path}: {e}"

    async def run_shell_command(self, command: str, dir_path: Optional[str] = None, extra_env: Optional[dict[str, str]] = None) -> str:
        """
        Executes a shell command in the workspace asynchronously.
        
        The command runs in the configured virtual environment (if present), ensuring access to installed packages.

        Args:
            command: The shell command to execute.
            dir_path: Optional working directory for the command, relative to the workspace root.
                      If not provided, defaults to the workspace root.
            extra_env: Optional dictionary of environment variables to add/override for this command.

        Returns:
            A structured string containing:
            - Command: The executed command
            - Directory: The directory where it ran
            - Stdout: Standard output of the command
            - Stderr: Standard error of the command
            - Exit Code: Integer exit code

        Example:
            >>> await run_shell_command("pytest tests/", dir_path=".")
            # Runs pytest in the root workspace directory.
        """
        try:
            env = os.environ.copy()
            if self.venv_path:
                # Prepend venv bin to PATH
                venv_bin = self.venv_path / "bin"
                env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
                # Unset PYTHONHOME if set, to ensure venv isolation
                env.pop("PYTHONHOME", None)
            
            # Merge extra_env if provided
            if extra_env:
                env.update(extra_env)

            # Determine CWD
            if dir_path:
                cwd = self._resolve_path(dir_path)
            else:
                cwd = self.workspace_root
            
            if not cwd.exists():
                 return f"Error: Directory not found at {cwd}"

            loop = asyncio.get_running_loop()
            try:
                result = await loop.run_in_executor(
                    None,
                    functools.partial(
                        subprocess.run,
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        cwd=cwd,
                        timeout=60, # Increased timeout slightly
                        env=env
                    )
                )
            except subprocess.TimeoutExpired:
                return (
                    f"Command: {command}\n"
                    f"Directory: {dir_path if dir_path else '(root)'}\n"
                    f"Error: Command timed out after 60 seconds."
                )

            # Format output similar to TS ShellTool
            output_parts = [
                f"Command: {command}",
                f"Directory: {dir_path if dir_path else '(root)'}",
                f"Stdout: {result.stdout.strip() if result.stdout else '(empty)'}",
                f"Stderr: {result.stderr.strip() if result.stderr else '(empty)'}",
                f"Exit Code: {result.returncode}",
            ]
            
            return "\n".join(output_parts)

        except Exception as e:
            return f"Error running command: {e}"

    async def search_files(self, pattern: str, path: str) -> str:
        """
        Searches for files matching a specific pattern using `grep -r`.
        
        Output is limited to 20 matches and 500 characters per line to prevent context explosion.

        Args:
            pattern: The pattern to search for (passed to grep). Can be a literal string.
                     Single quotes are automatically escaped.
            path: The directory path to search in, relative to the workspace root.

        Returns:
            The output of the grep command (stdout/stderr/exit code) formatted by `run_shell_command`.

        Example:
            >>> await search_files("def create_agent", ".")
            # Recursively searches for "def create_agent" in all files in the workspace.
        """
        # Escape single quotes in pattern to prevent shell injection/breaking
        safe_pattern = pattern.replace("'", "'\\''")
        # Use head to limit output and cut to limit line length
        cmd = f"grep -r '{safe_pattern}' '{path}' | head -n 20 | cut -c 1-500"
        return await self.run_shell_command(cmd)

    async def get_module_help(self, module_name: str) -> str:
        """
        Retrieves a summary of the public API for a Python module.
        
        This filters out private members (starting with '_') to provide a token-efficient
        overview of classes, functions, and submodules.

        Args:
            module_name: The name of the module to get help for (e.g., 'json', 'google.adk').

        Returns:
            A formatted string containing the module summary, or an error message.
        """
        # Validate module name to prevent arbitrary command execution
        if not module_name.replace(".", "").replace("_", "").isalnum():
             return "Error: Invalid module name. Only alphanumeric characters, dots, and underscores are allowed."
        
        script_content = r'''
import sys
import inspect
import pkgutil
import importlib

MAX_ITEMS = 20

def get_summary(obj, max_len=300):
    doc = inspect.getdoc(obj)
    if not doc:
        return ""
    
    # Take up to the first double newline (paragraph break) to get the main summary
    # and avoid listing all arguments if they are separated by blank lines.
    parts = doc.split('\n\n')
    summary = parts[0].strip()
    
    # Normalize whitespace (replace newlines in the paragraph with spaces)
    summary = " ".join(summary.split())
    
    if len(summary) > max_len:
        return summary[:max_len-3] + "..."
    return summary

def print_help(name):
    try:
        mod = importlib.import_module(name)
    except ImportError as e:
        print(f"Error: Could not import {name}: {e}")
        return

    print(f"Module: {name}")
    print(f"Doc: {get_summary(mod)}\n")

    # Submodules (if package)
    if hasattr(mod, "__path__"):
        submodules = []
        try:
            for _, subname, _ in pkgutil.iter_modules(mod.__path__):
                if not subname.startswith("_"):
                    submodules.append(subname)
        except Exception:
            pass 
            
        if submodules:
            print("Public Submodules:")
            for s in sorted(submodules):
                print(f"  {s}")
            print("")

    # Classes
    classes = []
    for n, o in inspect.getmembers(mod, inspect.isclass):
        if not n.startswith("_"):
            classes.append((n, o))
    
    if classes:
        print("Public Classes:")
        sorted_classes = sorted(classes, key=lambda x: x[0])
        display_classes = sorted_classes[:MAX_ITEMS]
        
        for n, o in display_classes:
            print(f"  class {n}: {get_summary(o)}")
            
            # Show public methods
            methods = []
            for mn, mo in inspect.getmembers(o):
                if not mn.startswith("_") and (inspect.isfunction(mo) or inspect.ismethod(mo)):
                     methods.append((mn, mo))
            
            # Sort methods: __init__ first, then alphabetical
            methods.sort(key=lambda x: (0 if x[0] == "__init__" else 1, x[0]))
            
            display_methods = methods[:10]
            
            for mn, mo in display_methods:
                 try:
                     sig = inspect.signature(mo)
                 except:
                     sig = "(...)"
                 print(f"    def {mn}{sig}")
                 # Add docstring for methods!
                 doc = get_summary(mo, max_len=150)
                 if doc:
                     print(f"      {doc}")
            
            if len(methods) > 10:
                print(f"    ... and {len(methods) - 10} more methods")
            print("") # Spacing between classes
                
        if len(classes) > MAX_ITEMS:
            print(f"... and {len(classes) - MAX_ITEMS} more classes")
        print("")

    # Functions
    funcs = []
    for n, o in inspect.getmembers(mod, inspect.isfunction):
        if not n.startswith("_"):
            funcs.append((n, o))
    
    if funcs:
        print("Public Functions:")
        sorted_funcs = sorted(funcs, key=lambda x: x[0])
        display_funcs = sorted_funcs[:MAX_ITEMS]
        
        for n, o in display_funcs:
            try:
                sig = inspect.signature(o)
            except:
                sig = "(...)"
            print(f"  def {n}{sig}: {get_summary(o)}")
            
        if len(funcs) > MAX_ITEMS:
            print(f"... and {len(funcs) - MAX_ITEMS} more functions")

if __name__ == "__main__":
    print_help(sys.argv[1])
'''
        
        run_id = uuid.uuid4().hex
        script_name = f"_help_runner_{run_id}.py"
        self.write_file(script_name, script_content)
        
        cmd = f"python3 {script_name} {module_name}"
        output = await self.run_shell_command(cmd)
        
        # Cleanup
        try:
            (self.workspace_root / script_name).unlink(missing_ok=True)
        except Exception:
            pass
            
        return output

    async def read_full_execution_logs(self) -> str:
        """
        Retrieves the full execution logs (Stdout/Stderr) from the most recent `run_adk_agent` call.
        Use this if the summary provided by `run_adk_agent` is insufficient for debugging.
        """
        return self.read_file("_last_run.log", limit=-1)

    async def run_adk_agent(self, prompt: str, model_name: str, agent_code: Optional[str] = None, agent_file: Optional[str] = None, initial_state: Optional[str] = None, api_key: Optional[str] = None) -> str:
        """
        Executes a Python ADK agent.
        
        You must provide EITHER `agent_code` (the full source code string) OR `agent_file` (the path to an existing file).
        Passing `agent_file` is preferred to save tokens if the file already exists in the workspace.
        
        This tool runs the agent and returns a **SUMMARY** of the execution logs to save tokens.
        If the agent fails or you need more details, use `read_full_execution_logs` to see the complete output.

        Args:
            prompt: The user input prompt or task description to send to the created agent for execution.
            model_name: The name of the LLM model to pass to the `create_agent` function (e.g., "gemini-2.5-flash").
            agent_code: The complete, executable Python source code defining the agent.
            agent_file: The path to an existing Python file in the workspace containing the agent code.
            initial_state: An optional JSON string representing the initial session state for the agent.
                           Example: '{"user_name": "Alice"}'
            api_key: Optional API key to use for this execution. If provided, it sets GEMINI_API_KEY env var.

        Returns:
            A **summary** string containing the agent's response and partial execution logs.
        """
        
        if agent_code and agent_file:
            return "Error: Please provide either `agent_code` OR `agent_file`, not both."
        if not agent_code and not agent_file:
            return "Error: You must provide either `agent_code` or `agent_file`."
            
        # Parse initial_state if provided as string
        initial_state_dict = None
        if initial_state:
            import json
            try:
                initial_state_dict = json.loads(initial_state)
            except json.JSONDecodeError as e:
                return f"Error parsing initial_state JSON: {e}"

        # We need to run this in the venv to access google-adk.
        # We'll create a temporary python script in the workspace that does the work.
        
        runner_script_content = r'''
import sys
import argparse
import importlib.util
import asyncio
import io
import traceback
import uuid
import os
import json

# Try importing ADK modules. If they fail, we can't run.
try:
    from google.adk.apps import App
    from google.adk.runners import InMemoryRunner
    from google.genai import types
except ImportError as e:
    print(f"Error: Failed to import google.adk. Ensure adk-python is installed in the environment.\n{e}")
    sys.exit(1)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-file", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--initial-state", type=str, default="{}") # Passed as JSON string
    args = parser.parse_args()

    # Parse initial_state from JSON string
    try:
        initial_state = json.loads(args.initial_state)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON for initial_state: {args.initial_state}")
        sys.exit(1)

    # 1. Load module dynamically
    # Use a unique name to ensure no conflicts if run repeatedly in same process (though we run in subprocess)
    module_name = f"dynamic_agent_{uuid.uuid4().hex}"
    
    # We need absolute path for importlib
    agent_file_path = os.path.abspath(args.agent_file)
    
    if not os.path.exists(agent_file_path):
        print(f"Error: Agent file not found at {agent_file_path}")
        sys.exit(1)

    try:
        spec = importlib.util.spec_from_file_location(module_name, agent_file_path)
        if not spec or not spec.loader:
             print(f"Error: Could not load spec for {agent_file_path}")
             sys.exit(1)
             
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception:
        print(f"Error loading agent code:\n{traceback.format_exc()}")
        sys.exit(1)

    if not hasattr(module, "create_agent"):
        print("Error: The provided code does not define a function `create_agent(model_name: str)`.")
        sys.exit(1)

    # 2. Instantiate Agent
    try:
        agent = module.create_agent(model_name=args.model_name)
    except Exception:
        print(f"Error during agent instantiation (create_agent):\n{traceback.format_exc()}")
        sys.exit(1)

    # 3. Execute with Stdout/Stderr Capture
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    result = ""
    execution_error = None
    
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        # Setup Runner
        app = App(name=f"runner_app_{uuid.uuid4().hex}", root_agent=agent)
        runner = InMemoryRunner(app=app)

        # Create Session
        session = await runner.session_service.create_session(
            app_name=app.name, user_id="runner-user", state=initial_state
        )

        # Run
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text=args.prompt)]),
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        result += part.text

    except Exception:
        execution_error = traceback.format_exc()
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
    
    logs = f"--- Logs ---\nStdout:\n{stdout_capture.getvalue()}\nStderr:\n{stderr_capture.getvalue()}"

    if execution_error:
        print(f"Agent Execution Failed:\n{execution_error}\n\n{logs}")
    else:
        print(f"Response: {result}\n\n{logs}")

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        run_id = uuid.uuid4().hex
        runner_filename = f"_adk_runner_{run_id}.py"
        files_to_clean = [runner_filename]

        if agent_code:
            # Write provided code to a temporary file
            agent_filename = f"agent_to_run_{run_id}.py"
            self.write_file(agent_filename, agent_code)
            files_to_clean.append(agent_filename)
        else:
            # Use provided file path
            agent_filename = agent_file
            # Don't delete the user's file!
            
            # Verify file exists
            resolved_path = self._resolve_path(agent_filename)
            if not resolved_path.exists():
                return f"Error: Agent file not found at {agent_filename}"

        # Write runner script
        self.write_file(runner_filename, runner_script_content)
        
        # Prepare initial_state argument
        # It's already parsed as dict, convert back to JSON string for the shell command
        initial_state_arg = "" 
        if initial_state_dict is not None:
            import json
            initial_state_arg = f"--initial-state {shlex.quote(json.dumps(initial_state_dict))}"

        # Construct command
        # Use shlex.quote for prompt to handle spaces/quotes safely
        cmd = f"python3 {runner_filename} --agent-file {agent_filename} --prompt {shlex.quote(prompt)} --model-name {shlex.quote(model_name)} {initial_state_arg}"
        
        # Configure extra env
        extra_env = {}
        if api_key:
            extra_env["GEMINI_API_KEY"] = api_key
        
        # Execute
        output = await self.run_shell_command(cmd, extra_env=extra_env)
        
        # Save full logs for on-demand retrieval
        self.write_file("_last_run.log", output)
        
        # Create summary
        if len(output) > 2000:
            summary = (
                output[:1000] 
                + f"\n... [Logs Truncated. {len(output)-2000} chars hidden. Use `read_full_execution_logs` to see all.] ...\n" 
                + output[-1000:]
            )
        else:
            summary = output

        # Cleanup
        try:
            for fname in files_to_clean:
                (self.workspace_root / fname).unlink(missing_ok=True)
                
            # Remove __pycache__ if generated
            import shutil
            pycache = self.workspace_root / "__pycache__"
            if pycache.exists():
                shutil.rmtree(pycache)
        except Exception:
            pass # Ignore cleanup errors
            
        return summary
