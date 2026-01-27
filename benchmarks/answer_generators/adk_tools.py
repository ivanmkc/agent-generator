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
import sys
from tools.benchmark_generator.models import TargetEntity
from tools.target_ranker.models import RankedTarget

# Try to import yaml
try:
    import yaml
except ImportError:
    yaml = None

# Try to import adk_knowledge_ext for advanced search
try:
    # Add the extension path relative to this file
    # benchmarks/answer_generators/adk_tools.py -> root -> tools/adk-knowledge-ext/src
    ext_path = Path(__file__).resolve().parents[3] / "tools/adk-knowledge-ext/src"
    if str(ext_path) not in sys.path:
        sys.path.append(str(ext_path))
    from adk_knowledge_ext.search import get_search_provider
    HAS_SEARCH_PROVIDER = True
except ImportError:
    HAS_SEARCH_PROVIDER = False

class AdkTools:
    def __init__(self, workspace_root: Path, venv_path: Path | None = None):
        self.workspace_root = workspace_root
        self.venv_path = venv_path
        self._stats_index = None
        self._coocc_index = None
        self._search_provider = None
        self._load_stats_index()
        self._load_coocc_index()
        self._init_search_provider()

    def _init_search_provider(self):
        """Initializes the search provider if available."""
        if HAS_SEARCH_PROVIDER and yaml:
            try:
                targets = self._load_ranked_targets()
                if targets:
                    self._search_provider = get_search_provider("bm25")
                    # Convert Pydantic models to dicts for the provider
                    items = [t.model_dump() for t in targets]
                    self._search_provider.build_index(items)
            except Exception as e:
                print(f"Failed to initialize search provider: {e}")

    def _load_stats_index(self):
        """Loads the pre-calculated API usage statistics from benchmarks/adk_stats.yaml."""
        stats_path = Path("benchmarks/adk_stats.yaml")
        if stats_path.exists() and yaml:
            try:
                with open(stats_path, "r", encoding="utf-8") as f:
                    self._stats_index = yaml.safe_load(f)
            except Exception:
                pass

    def _load_coocc_index(self):
        """Loads the co-occurrence matrix from benchmarks/adk_cooccurrence.json."""
        coocc_path = Path("benchmarks/adk_cooccurrence.json")
        if coocc_path.exists():
            try:
                with open(coocc_path, "r", encoding="utf-8") as f:
                    self._coocc_index = json.load(f)
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
            
            # Default ignores if not provided
            if ignore is None:
                ignore = ['.git', '__pycache__', 'venv', 'env', 'node_modules', '.DS_Store', '*.pyc']

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

    async def run_shell_command(self, command: str | List[str], dir_path: Optional[str] = None, extra_env: Optional[Any] = None) -> str:
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
            
            # If command is a string, use shell=True. If list, use shell=False.
            is_shell = isinstance(command, str)
            
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, functools.partial(
                subprocess.run, 
                command, 
                shell=is_shell, 
                capture_output=True, 
                text=True, 
                cwd=cwd, 
                timeout=60, 
                env=env
            ))
            
            cmd_str = command if isinstance(command, str) else " ".join(command)
            output_parts = [f"Command: {cmd_str}", f"Directory: {dir_path or '(root)'}", f"Stdout: {result.stdout.strip() or '(empty)'}", f"Stderr: {result.stderr.strip() or '(empty)'}", f"Exit Code: {result.returncode}"]
            return "\n".join(output_parts)
        except Exception as e:
            return f"Error running command: {e}"

    async def search_files(self, pattern: str, path: str) -> str:
        """Searches for files matching a specific pattern using `grep -r`."""
        safe_pattern = pattern.replace("'", "'\\''")
        # Exclude common noise directories
        exclude_args = "--exclude-dir=venv --exclude-dir=env --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=node_modules"
        cmd = f"grep -r {exclude_args} '{safe_pattern}' '{path}' | head -n 20 | cut -c 1-500"
        return await self.run_shell_command(cmd)

    def get_api_associations(self, entity_name: str, threshold: float = 0.1) -> str:
        """Returns modules/classes statistically likely to be used with the given entity."""
        if not self._coocc_index:
            return "Error: Co-occurrence index not loaded."
        
        associations = self._coocc_index.get("associations", [])
        # Find associations where 'context' is the entity
        related = [a for a in associations if a["context"] == entity_name and a["probability"] >= threshold]
        
        if not related:
            # Try fuzzy match (prefix)
            related = [a for a in associations if entity_name.startswith(a["context"]) and a["probability"] >= threshold]

        if not related:
            return f"No associations found for '{entity_name}' above threshold {threshold}."

        output = [f"# Statistical Associations for: {entity_name}"]
        for a in related[:10]:
            output.append(f"- {a['target']} (Prob: {a['probability']:.2f}, Support: {a['support']})")
        
        return "\n".join(output)

    async def get_module_help(self, module_name: str, depth: int = 0) -> str:
        """Retrieves a summary of the public API for a Python module with statistical prioritization."""
        # Check if we have pre-calculated stats
        if self._stats_index:
             stats_help = self._get_statistical_module_help(module_name)
             # If the stats index actually found something, return it.
             # Otherwise, continue to runtime fallback.
             if "Fallback to runtime search" not in stats_help:
                 return stats_help
        
        # Fallback to runtime inspection if no index or no stats for this module
        return await self.inspect_fqn(module_name, depth)

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
                if arg_data['freq'] < 0.01 and arg_data['count'] < 1:
                    continue # Prune very rare args
                
                req_str = "REQUIRED" if arg_data['freq'] == 1.0 else f"Used {int(arg_data['freq']*100)}%"
                output.append(f"    {arg},  # {req_str}")
                lines_written += 1
            
            output.append("  )")
            lines_written += 5
            
        return "\n".join(output)

    def _load_ranked_targets(self) -> List[RankedTarget]:
        candidates = [
            self.workspace_root / "tools/benchmark_generator/data/ranked_targets.yaml",
            self.workspace_root / "ranked_targets.yaml",
            Path("tools/benchmark_generator/data/ranked_targets.yaml"),
            Path("ranked_targets.yaml"),
            Path(__file__).resolve().parent.parent.parent / "ranked_targets.yaml",
            Path(__file__).resolve().parent.parent / "benchmark_generator/data/ranked_targets.yaml"
        ]
        
        index_path = None
        for p in candidates:
            if p.exists():
                index_path = p
                break
        
        if not index_path:
            return []

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f)
            return [RankedTarget(**item) for item in raw_data]
        except Exception:
            return []

    def inspect_ranked_target(self, fqn: str) -> str:
        """
        Inspects a target using the offline ranked_targets.yaml index.
        """
        data = self._load_ranked_targets()
        if not data:
            return "Error: ranked_targets.yaml not found or empty."
            
        target = next((item for item in data if item.id == fqn), None)
        if not target:
            return f"Target '{fqn}' not found in ranked index."
            
        output = [f"=== Inspection: {target.id} ==="]
        output.append(f"Type: {target.type}")
        output.append(f"Rank: {target.rank}")
        output.append(f"Usage Score: {target.usage_score}")
        output.append(f"\n[Docstring]\n{target.docstring}")
        
        if target.methods:
            output.append("\n[Methods]")
            for m in target.methods:
                doc = (m.docstring or "").split('\n')[0][:100]
                output.append(f"  - {m.signature}\n    Doc: {doc}")
                
        if target.properties:
            output.append("\n[Properties]")
            for p in target.properties:
                doc = (p.docstring or "").split('\n')[0][:100]
                output.append(f"  - {p.signature}\n    Doc: {doc}")

        if target.inherited_methods:
            output.append("\n[Inherited Methods]")
            for base, methods in target.inherited_methods.items():
                output.append(f"  From {base}:")
                for m in methods:
                    output.append(f"    - {m.signature}")

        return "\n".join(output)

    async def inspect_fqn(self, fqn: str, depth: int = 0) -> str:
        """
        Inspects a Python object (class or module) given its fully qualified name.
        Uses runtime inspection to reveal docstrings, signatures, and hierarchy.
        """
        project_root = Path(__file__).resolve().parent.parent.parent
        inspector_script = project_root / "tools" / "utils" / "inspect_fqn.py"
        
        # Build the execution command as a list to handle spaces in absolute paths safely
        cmd = ["python3", str(inspector_script), fqn, "--depth", str(depth)]
        
        return await self.run_shell_command(cmd)

    def list_ranked_targets(self, page: int = 1, page_size: int = 100) -> str:
        """
        Lists ranked ADK targets from the index, paginated.
        """
        try:
            if not yaml:
                return "Error: PyYAML not installed."

            data = self._load_ranked_targets()
            if not data:
                return "Error: ranked_targets.yaml not found or empty."
            
            total_items = len(data)
            max_page = (total_items + page_size - 1) // page_size
            
            if page < 1: page = 1
            
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            if start_idx >= total_items:
                return f"Page {page} is out of range. Total items: {total_items} (max page {max_page})."
            
            page_items = data[start_idx:end_idx]
            
            lines = [f"--- Ranked Targets (Page {page} of {max_page}) ---"]
            lines.append(f"Showing items {start_idx + 1} to {min(end_idx, total_items)} of {total_items}")
            
            for item in page_items:
                fqn = item.id
                rank = item.rank
                doc = item.docstring or "No description."
                doc_summary = doc.split('\n')[0].strip()
                if len(doc_summary) > 80: doc_summary = doc_summary[:77] + "..."
                lines.append(f"[{rank}] {fqn}: {doc_summary}")
                
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error reading ranked targets: {e}"

    def search_ranked_targets(self, query: str | list[str], page: int = 1, page_size: int = 10) -> str:
        """
        Searches the ranked targets index for FQNs or docstrings matching the query (or list of queries), paginated.
        """
        if isinstance(query, list):
            q_str = " ".join([str(q) for q in query])
        else:
            q_str = str(query)

        if self._search_provider:
            # Use advanced search provider (BM25 -> Keyword)
            matches = self._search_provider.search(q_str, page=page, page_size=page_size)
            
            # Format results
            if not matches:
                return f"No targets found matching: {q_str}."
            
            # Retrieve total count is not directly exposed by search(), but page=1/size=10 implies partial.
            # We can approximate total or just show page info.
            # search() returns just the page slice.
            
            output = [f"--- Search Results for '{q_str}' (Page {page}) ---"]
            
            for score, item in matches:
                fqn = item.get("id") or item.get("fqn")
                rank = item.get("rank", "?")
                doc = item.get("docstring") or "No description."
                doc_summary = doc.split('\n')[0].strip()
                if len(doc_summary) > 80: doc_summary = doc_summary[:77] + "... "
                output.append(f"[{rank}] {fqn}: {doc_summary}")
                
            return "\n".join(output)

        try:
            if not yaml:
                return "Error: PyYAML not installed."

            data = self._load_ranked_targets()
            if not data:
                return "Error: ranked_targets.yaml not found or empty."
            
            if isinstance(query, list):
                queries = [str(q).lower() for q in query]
            else:
                queries = [str(query).lower()]

            results = []
            for item in data:
                fqn = item.id.lower()
                doc = (item.docstring or "").lower()
                # Match if ANY query term is present in FQN or docstring
                if any(q in fqn or q in doc for q in queries):
                    results.append(item)
            
            if not results:
                q_str = ", ".join(queries)
                return f"No targets found matching: {q_str}."
            
            total_items = len(results)
            max_page = (total_items + page_size - 1) // page_size
            
            if page < 1: page = 1
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            if start_idx >= total_items:
                q_str = ", ".join(queries)
                return f"Page {page} is out of range for search '{q_str}'. Total results: {total_items} (max page {max_page})."
            
            page_items = results[start_idx:end_idx]
            
            q_str = ", ".join(queries)
            output = [f"--- Search Results for '{q_str}' (Page {page} of {max_page}, Total: {total_items}) ---"]
            output.append(f"Showing items {start_idx + 1} to {min(end_idx, total_items)}")
            
            for item in page_items:
                fqn = item.id
                rank = item.rank
                doc = item.docstring or "No description."
                doc_summary = doc.split('\n')[0].strip()
                if len(doc_summary) > 80: doc_summary = doc_summary[:77] + "... "
                output.append(f"[{rank}] {fqn}: {doc_summary}")
                
            return "\n".join(output)
        except Exception as e:
            return f"Error searching ranked targets: {e}"

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

    async def run_adk_agent(
        self, 
        prompt: str, 
        model_name: str, 
        agent_code: Optional[str] = None, 
        agent_file: Optional[str] = None, 
        initial_state: Optional[str] = None, 
        api_key: Optional[str] = None
    ) -> str:
        """
        Executes a candidate ADK agent in a sandboxed runtime environment.

        Methodology:
        1. Validates input (must provide either agent_code or an agent_file path).
        2. If agent_code is provided, writes it to a temporary file in the workspace.
        3. Invokes the standalone `tools/utils/adk_agent_runner.py` script.
        4. The runner utility dynamically imports the agent, sets up an `InMemoryRunner`, 
           and executes the provided prompt.
        5. It captures all stdout/stderr from the agent's execution for forensic debugging.

        Args:
            prompt: The text instruction to send to the agent.
            model_name: The name of the LLM to use (e.g., 'gemini-2.0-flash').
            agent_code: The Python source code for the agent (defining create_agent).
            agent_file: A relative path to an existing agent file.
            initial_state: An optional JSON string representing the starting session state.
            api_key: An optional Gemini API key to override the environment default.

        Returns:
            A string containing the agent's response and its execution logs.
        """
        if agent_code and agent_file:
             return "Error: Provide either `agent_code` OR `agent_file`, not both."
        if not agent_code and not agent_file:
             return "Error: You must provide either `agent_code` or `agent_file` to run an agent."
        
        # Security/Tracing ID
        run_id = uuid.uuid4().hex
        
        # Prepare the agent file
        target_agent_file = agent_file
        if agent_code:
            target_agent_file = f"ag_tmp_{run_id}.py"
            self.write_file(target_agent_file, agent_code)
        
        # Decouple execution into a standalone script
        project_root = Path(__file__).resolve().parent.parent.parent
        runner_script = project_root / "tools" / "utils" / "adk_agent_runner.py"
        
        # Build the command as a list for safe path handling
        cmd = [
            "python3", 
            str(runner_script), 
            "--agent-file", target_agent_file, 
            "--prompt", prompt, 
            "--model-name", model_name
        ]
        if initial_state:
            cmd.extend(["--initial-state", initial_state])
        
        # Run the command. The run_shell_command method ensures virtualenv 
        # pathing is correct and captures result parts.
        output = await self.run_shell_command(cmd, extra_env={"GEMINI_API_KEY": api_key} if api_key else None)
        
        # Persist the full output for forensic trace analysis
        self.write_file("_last_agent_run.log", output)
        
        # Cleanup temporary code file
        try:
             if agent_code:
                 (self.workspace_root / target_agent_file).unlink(missing_ok=True)
        except Exception:
             pass
             
        # Return a snippet of the result to keep the agent's context window clean
        return output[:2000] + "..." if len(output) > 2000 else output