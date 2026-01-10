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
from typing import List, Optional, Any, Dict
import json
import asyncio
import functools
import ast

# Try to import yaml
try:
    import yaml
except ImportError:
    yaml = None

class AdkTools:
    def __init__(self, workspace_root: Path, venv_path: Path | None = None):
        self.workspace_root = workspace_root
        self.venv_path = venv_path
        self._stats_index = None
        self._load_stats_index()

    def _load_stats_index(self):
        """Loads the pre-calculated API usage statistics from benchmarks/adk_stats.yaml."""
        stats_path = Path("benchmarks/adk_stats.yaml")
        if stats_path.exists() and yaml:
            try:
                with open(stats_path, "r", encoding="utf-8") as f:
                    self._stats_index = yaml.safe_load(f)
            except Exception:
                pass

    def _resolve_path(self, path_str: str) -> Path:
        """Resolves a path relative to the workspace root and ensures it's safe."""
        path = Path(path_str)
        if path.is_absolute():
            try:
                path = path.relative_to(self.workspace_root)
            except ValueError:
                 if not str(path).startswith(str(self.workspace_root)):
                     pass 

        full_path = (self.workspace_root / path).resolve() 
        if not str(full_path).startswith(str(self.workspace_root.resolve())):
            raise ValueError(f"Access denied: Path {path_str} resolves to {full_path} which is outside the workspace {self.workspace_root}")
        return full_path

    def read_file(self, file_path: str, offset: int = 0, limit: int = 1000) -> str:
        """Reads and returns the content of a specified file."""
        try:
            full_path = self._resolve_path(file_path)
            if not full_path.exists():
                 return f"Error: File not found at {full_path}"
            if not full_path.is_file():
                return f"Error: Path {full_path} is not a file."
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                return f"Error: File {file_path} appears to be binary or not UTF-8 encoded."

            total_lines = len(lines)
            if offset < 0: offset = 0
            if offset >= total_lines and total_lines > 0:
                return f"Error: Offset {offset} is beyond the end of the file."
            
            MAX_HARD_LIMIT = 2000
            if limit == -1 or limit > MAX_HARD_LIMIT: limit = MAX_HARD_LIMIT
            end_index = min(offset + limit, total_lines)
            selected_lines = lines[offset:end_index]
            
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
            if (end_index < total_lines) or (offset > 0) or lines_width_truncated:
                msg = f"IMPORTANT: The file content has been truncated.\n--- FILE CONTENT (truncated) ---\n{content}"
                return msg
            else:
                return content
        except Exception as e:
            return f"Error reading file {file_path}: {e}"

    def replace_text(self, file_path: str, old_string: str, new_string: str, expected_replacements: Optional[int] = None) -> str:
        """Replaces text within a file."""
        try:
            full_path = self._resolve_path(file_path)
            if not full_path.exists(): return f"Error: File not found at {full_path}"
            with open(full_path, "r", encoding="utf-8") as f: content = f.read()
            count = content.count(old_string)
            if count == 0: return f"Error: `old_string` not found."
            expected = expected_replacements if expected_replacements is not None else 1
            if count != expected: return f"Error: Expected {expected} matches, found {count}."
            new_content = content.replace(old_string, new_string)
            with open(full_path, "w", encoding="utf-8") as f: f.write(new_content)
            return f"Successfully replaced {count} occurrence(s) in {file_path}."
        except Exception as e:
            return f"Error replacing text: {e}"

    def write_file(self, file_path: str, content: str) -> str:
        """Writes content to a specified file."""
        try:
            full_path = self._resolve_path(file_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f: f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {e}"

    def list_directory(self, dir_path: str, ignore: Optional[List[str]] = None) -> str:
        """Lists files and subdirectories within a specified directory."""
        try:
            full_path = self._resolve_path(dir_path)
            if not full_path.exists(): return f"Error: Directory not found at {full_path}"
            if not full_path.is_dir(): return f"Error: Path {full_path} is not a directory."
            entries = []
            with os.scandir(full_path) as it:
                for entry in it:
                    if ignore:
                        if any(fnmatch.fnmatch(entry.name, p) for p in ignore): continue
                    entries.append({"name": entry.name, "is_dir": entry.is_dir()})
            if not entries: return f"Directory {dir_path} is empty."
            entries.sort(key=lambda x: (not x["is_dir"], x["name"]))
            output = [f"Directory listing for {dir_path}:"]
            for entry in entries:
                prefix = "[DIR] " if entry["is_dir"] else ""
                output.append(f"{prefix}{entry['name']}")
            return "\n".join(output)
        except Exception as e:
            return f"Error listing directory: {e}"

    def read_repo_file(self, repo_name: str, file_path: str, offset: int = 0, limit: int = 1000) -> str:
        """Reads a file from a specific repository in the workspace."""
        return self.read_file(f"repos/{repo_name}/{file_path}", offset=offset, limit=limit)

    def list_repo_directory(self, repo_name: str, dir_path: str = ".", ignore: Optional[List[str]] = None) -> str:
        """Lists files in a specific repository directory."""
        return self.list_directory(f"repos/{repo_name}/{dir_path}", ignore=ignore)

    async def run_shell_command(self, command: str, dir_path: Optional[str] = None, extra_env: Optional[dict[str, str]] = None) -> str:
        """Executes a shell command in the workspace asynchronously."""
        try:
            env = os.environ.copy()
            if self.venv_path:
                venv_bin = self.venv_path / "bin"
                env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
                env.pop("PYTHONHOME", None)
            if extra_env: env.update(extra_env)
            cwd = self._resolve_path(dir_path) if dir_path else self.workspace_root
            if not cwd.exists(): return f"Error: Directory not found at {cwd}"
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, functools.partial(subprocess.run, command, shell=True, capture_output=True, text=True, cwd=cwd, timeout=60, env=env))
            output_parts = [f"Command: {command}", f"Directory: {dir_path or '(root)'}", f"Stdout: {result.stdout.strip() or '(empty)'}", f"Stderr: {result.stderr.strip() or '(empty)'}", f"Exit Code: {result.returncode}"]
            return "\n".join(output_parts)
        except Exception as e:
            return f"Error running command: {e}"

    async def search_files(self, pattern: str, path: str) -> str:
        """Searches for files matching a specific pattern using `grep -r`."""
        safe_pattern = pattern.replace("'", "'\\''")
        cmd = f"grep -r '{safe_pattern}' '{path}' | head -n 20 | cut -c 1-500"
        return await self.run_shell_command(cmd)

    async def get_module_help(self, module_name: str, depth: int = 0) -> str:
        """Retrieves a summary of the public API for a Python module with statistical prioritization."""
        # Check if we have pre-calculated stats
        if self._stats_index:
             return self._get_statistical_module_help(module_name)
        
        # Fallback to runtime inspection if no index
        return await self._get_runtime_module_help(module_name, depth)

    def _get_statistical_module_help(self, module_name: str, max_tokens: int = 1500) -> str:
        """Curates API help based on usage frequency from api_metadata.yaml."""
        if not self._stats_index:
            return "Error: Statistical index not loaded."
            
        relevant = {k: v for k, v in self._stats_index.items() if k.startswith(module_name)}
        if not relevant:
            return f"No statistical data for module '{module_name}'. Fallback to runtime search."

        output = [f"# Statistical API Discovery: {module_name}"]
        # Sort symbols by total calls
        sorted_symbols = sorted(relevant.items(), key=lambda x: x[1]['total_calls'], reverse=True)
        
        # Simple budget estimation: ~20 tokens per line
        budget = max_tokens // 20
        lines_written = 0
        
        for fqn, data in sorted_symbols:
            if lines_written > budget:
                output.append(f"# ... {len(sorted_symbols) - sorted_symbols.index((fqn, data))} more symbols hidden.")
                break
                
            short_name = fqn.split('.')[-1]
            output.append(f"class {short_name}:")
            output.append(f"  # Total usages in codebase: {data['total_calls']}")
            output.append("  def __init__(")
            
            # Sort args by frequency
            args = data.get("args", {})
            sorted_args = sorted(args.items(), key=lambda x: x[1]['freq'], reverse=True)
            
            for arg, arg_data in sorted_args:
                if arg_data['freq'] < 0.1 and arg_data['count'] < 5:
                    continue # Prune rare args
                
                req_str = "REQUIRED" if arg_data['freq'] == 1.0 else f"Used {int(arg_data['freq']*100)}%"
                output.append(f"    {arg},  # {req_str}")
                lines_written += 1
            
            output.append("  )")
            lines_written += 5
            
        return "\n".join(output)

    async def _get_runtime_module_help(self, module_name: str, depth: int = 0) -> str:
        """Existing inspect-based discovery tool."""
        if not module_name.replace(".", "").replace("_", "").isalnum():
             return "Error: Invalid module name."
        script_content = r'''
import sys, inspect, pkgutil, importlib
def get_summary(obj, max_len=300):
    doc = inspect.getdoc(obj)
    if not doc: return ""
    summary = " ".join(doc.split('\n\n')[0].strip().split())
    return summary[:max_len-3] + "..." if len(summary) > max_len else summary
def print_help(name, current_depth=0, max_depth=0):
    indent = "  " * current_depth
    try: mod = importlib.import_module(name)
    except Exception as e: return
    print(f"{indent}Module: {name}\n{indent}Doc: {get_summary(mod)}\n")
    for n, o in inspect.getmembers(mod, inspect.isclass):
        if n.startswith("_"): continue
        try: sig = inspect.signature(o)
        except: sig = "(...)"
        print(f"{indent}  class {n}{sig}: {get_summary(o)}")
        methods = [(mn, mo) for mn, mo in inspect.getmembers(o) if not mn.startswith("_") and (inspect.isfunction(mo) or inspect.ismethod(mo))]
        for mn, mo in sorted(methods, key=lambda x: (0 if x[0] == "__init__" else 1, x[0]))[:5]:
            try: msig = inspect.signature(mo)
            except: msig = "(...)"
            print(f"{indent}    def {mn}{msig}")
    if current_depth < max_depth and hasattr(mod, "__path__"):
        for _, subname, _ in pkgutil.iter_modules(mod.__path__):
            if not subname.startswith("_"): print_help(f"{name}.{subname}", current_depth + 1, max_depth)
if __name__ == "__main__":
    print_help(sys.argv[1], 0, int(sys.argv[2]) if len(sys.argv) > 2 else 0)
'''
        run_id = uuid.uuid4().hex
        script_name = f"_help_runner_{run_id}.py"
        self.write_file(script_name, script_content)
        cmd = f"python3 {script_name} {module_name} {depth}"
        output = await self.run_shell_command(cmd)
        try: (self.workspace_root / script_name).unlink(missing_ok=True)
        except Exception: pass
        return output

    def read_definitions(self, file_path: str) -> str:
        """Reads simplified python definitions using AST."""
        try:
            full_path = self._resolve_path(file_path)
            if full_path.is_dir():
                init = full_path / "__init__.py"
                if init.exists(): return self.read_definitions(str(init))
                return f"Directory {file_path}:\n{self.list_directory(file_path)}"
            if not full_path.exists() and not file_path.endswith(".py"):
                try_path = file_path + ".py"
                if self._resolve_path(try_path).exists(): return self.read_definitions(try_path)
            content = self.read_file(file_path)
            if content.startswith("Error:"): return content
            tree = ast.parse(content)
            lines = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    lines.append(f"class {node.name}:")
                    for body_item in node.body:
                        if isinstance(body_item, ast.FunctionDef) and not body_item.name.startswith("_") or body_item.name == "__init__":
                            lines.append(f"  def {body_item.name}(...):")
            return "\n".join(lines) or "No public classes found."
        except Exception as e: return f"Error: {e}"

    async def read_full_execution_logs(self) -> str:
        return self.read_file("_last_run.log", limit=-1)

    async def run_adk_agent(self, prompt: str, model_name: str, agent_code: Optional[str] = None, agent_file: Optional[str] = None, initial_state: Optional[str] = None, api_key: Optional[str] = None) -> str:
        if agent_code and agent_file: return "Error: Provide only one."
        if not agent_code and not agent_file: return "Error: Provide code or file."
        initial_state_dict = json.loads(initial_state) if initial_state else None
        runner_script = r'''
import sys, argparse, importlib.util, asyncio, io, traceback, uuid, os, json
try: from google.adk.apps import App; from google.adk.runners import InMemoryRunner; from google.genai import types
except ImportError: sys.exit(1)
async def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--agent-file"); parser.add_argument("--prompt"); parser.add_argument("--model-name"); parser.add_argument("--initial-state", default="{}"); args = parser.parse_args()
    try:
        spec = importlib.util.spec_from_file_location("mod", os.path.abspath(args.agent_file)); module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        agent = module.create_agent(model_name=args.model_name); stdout = io.StringIO(); stderr = io.StringIO(); original_stdout = sys.stdout; original_stderr = sys.stderr
        sys.stdout = stdout; sys.stderr = stderr; app = App(name="app", root_agent=agent); runner = InMemoryRunner(app=app)
        session = await runner.session_service.create_session(app_name=app.name, user_id="user", state=json.loads(args.initial_state))
        result = ""
        async for event in runner.run_async(user_id=session.user_id, session_id=session.id, new_message=types.Content(role="user", parts=[types.Part(text=args.prompt)])):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text: result += part.text
        sys.stdout = original_stdout; sys.stderr = original_stderr
        print(f"Response: {result}\n\n--- Logs ---\nStdout:\n{stdout.getvalue()}\nStderr:\n{stderr.getvalue()}")
    except Exception: print(traceback.format_exc())
asyncio.run(main())
'''
        run_id = uuid.uuid4().hex
        runner_file = f"_ad_run_{run_id}.py"
        self.write_file(runner_file, runner_script)
        if agent_code:
            agent_file = f"ag_{run_id}.py"
            self.write_file(agent_file, agent_code)
        state_arg = f"--initial-state {shlex.quote(json.dumps(initial_state_dict))}" if initial_state_dict else ""
        cmd = f"python3 {runner_file} --agent-file {agent_file} --prompt {shlex.quote(prompt)} --model-name {shlex.quote(model_name)} {state_arg}"
        output = await self.run_shell_command(cmd, extra_env={"GEMINI_API_KEY": api_key} if api_key else None)
        self.write_file("_last_run.log", output)
        try:
             Path(runner_file).unlink(missing_ok=True)
             if agent_code: Path(agent_file).unlink(missing_ok=True)
        except: pass
        return output[:2000] + "..." if len(output) > 2000 else output