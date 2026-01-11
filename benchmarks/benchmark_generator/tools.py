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

"""Tools for the Prismatic Benchmark Generator agents."""

import ast
import os
import sys
import io
import time
import json
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter

from google.adk.tools import ToolContext
from benchmarks.benchmark_generator.models import TargetMethod, GoldenSnapshot, DistractorOption, ValidationStatus, TargetParameter, TargetType
from benchmarks.benchmark_generator.irt import IRTManager

# --- Usage Analysis ---

class UsageVisitor(ast.NodeVisitor):
    """AST Visitor to count function calls and argument usage."""
    def __init__(self):
        # Maps FQN -> {"call_count": int, "arg_usage": Counter}
        self.stats = defaultdict(lambda: {"call_count": 0, "arg_usage": Counter()})
        self.imports = {}

    def visit_Import(self, node):
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name
            if name == "*": continue
            full_name = f"{module}.{name}" if module else name
            self.imports[asname] = full_name
        self.generic_visit(node)

    def visit_Call(self, node):
        func_name = self._get_func_name(node.func)
        if func_name:
            resolved = self._resolve_name(func_name)
            self.stats[resolved]["call_count"] += 1
            for keyword in node.keywords:
                if keyword.arg:
                    self.stats[resolved]["arg_usage"][keyword.arg] += 1
        self.generic_visit(node)

    def _get_func_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_func_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        return None

    def _resolve_name(self, name):
        if not name: return name
        parts = name.split('.')
        root = parts[0]
        if root in self.imports:
            resolved_root = self.imports[root]
            return f"{resolved_root}.{'.'.join(parts[1:])}" if len(parts) > 1 else resolved_root
        return name

# --- Scanner (Cartographer) Logic ---

def scan_repository(repo_path: str, tool_context: ToolContext, coverage_file: Optional[str] = None) -> str:
    """
    Scans the repository for Python methods suitable for benchmarking.
    Acts as the 'Cartographer' by mapping topology:
    - Class hierarchies
    - API surfaces
    - Dependency graphs (imports)
    - Usage statistics (call counts)
    """
    root_dir = Path(repo_path).resolve()
    if not root_dir.exists():
        return json.dumps({"error": f"Path {repo_path} (resolved to {root_dir}) does not exist."})

    # Load coverage data if provided
    if not coverage_file:
        coverage_file = tool_context.session.state.get("coverage_file_path")

    coverage_data = None
    if coverage_file:
        cov_path = Path(coverage_file)
        if cov_path.exists():
            try:
                coverage_json = json.loads(cov_path.read_text())
                coverage_data = coverage_json.get("files", {})
            except Exception:
                pass

    targets = []
    all_files = []
    ignored_dirs = {".git", ".vscode", ".gemini", "__pycache__", "env", "venv", "node_modules", "dist", "build"}
    
    # 1. Collect all python files
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith(".py") and not file.startswith("test_") and not file.startswith("."):
                all_files.append(Path(root) / file)

    # 2. Usage Analysis Pass
    usage_visitor = UsageVisitor()
    for file_path in all_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            usage_visitor.visit(tree)
        except Exception:
            pass
            
    usage_stats = usage_visitor.stats

    # 3. Definition Pass
    for full_path in all_files:
        try:
            relative_path = full_path.relative_to(root_dir)
            
            # Construct module name from path (naive)
            module_parts = list(relative_path.parts)
            if module_parts[-1] == "__init__.py":
                module_parts.pop()
            else:
                module_parts[-1] = module_parts[-1][:-3] # remove .py
            module_name = ".".join(module_parts)

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Map Dependencies (Imports)
            dependencies = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.append(node.module)

            # Map Hierarchy and Methods
            class Visitor(ast.NodeVisitor):
                def __init__(self):
                    self.current_class = None
                    self.current_parents = []

                def visit_ClassDef(self, node):
                    old_class = self.current_class
                    old_parents = self.current_parents
                    
                    self.current_class = node.name
                    self.current_parents = [
                        ast.unparse(base) if hasattr(ast, "unparse") else str(base) 
                        for base in node.bases
                    ]
                    
                    self.generic_visit(node)
                    
                    self.current_class = old_class
                    self.current_parents = old_parents

                def visit_FunctionDef(self, node):
                    if node.name.startswith("_") and not node.name.startswith("__"):
                        return
                    
                    docstring = ast.get_docstring(node)
                    complexity = node.end_lineno - node.lineno if hasattr(node, "end_lineno") else 0
                    
                    if complexity < 3:
                        return
                    
                    # Construct FQN for usage lookup
                    if self.current_class:
                        fqn = f"{module_name}.{self.current_class}.{node.name}"
                    else:
                        fqn = f"{module_name}.{node.name}"
                    
                    # Lookup usage
                    stats = usage_stats.get(fqn, {})
                    call_count = stats.get("call_count", 0)
                    arg_usage = stats.get("arg_usage", {})
                    
                    # Construct parameters list
                    params = []
                    for arg in node.args.args:
                        p_name = arg.arg
                        p_count = arg_usage.get(p_name, 0)
                        params.append(TargetParameter(name=p_name, usage_count=p_count))

                    targets.append({
                        "file_path": str(relative_path),
                        "class_name": self.current_class,
                        "parent_classes": self.current_parents,
                        "method_name": node.name,
                        "code_signature": f"def {node.name}(...):", 
                        "docstring": docstring,
                        "complexity_score": float(complexity),
                        "usage_score": call_count,
                        "dependencies": dependencies,
                        "parameters": params,
                        "type": TargetType.METHOD
                    })

            Visitor().visit(tree)
        except Exception as e:
            pass
    
    tool_context.session.state["scanned_targets"] = targets
    tool_context.session.state["coverage_data"] = coverage_data
    return f"Cartographer scan complete: {len(targets)} targets mapped with usage stats."

def get_prioritized_target(tool_context: ToolContext) -> str:
    """
    Retrieves the next best target from the scanned list, prioritized by Usage, IRT and Coverage.
    Returns the target JSON or 'DONE'.
    """
    targets = tool_context.session.state.get("scanned_targets", [])
    if not targets:
        return json.dumps({"status": "EMPTY"})
    
    processed_list = tool_context.session.state.get("processed_targets_list", [])
    processed_set = set(processed_list)
    
    candidates = [t for t in targets if (t["file_path"] + "::" + t["method_name"]) not in processed_set]
    
    if not candidates:
        return json.dumps({"status": "DONE"})
    
    irt_file = tool_context.session.state.get("irt_file")
    irt_manager = IRTManager(irt_file)
    coverage_data = tool_context.session.state.get("coverage_data")

    def score(t):
        # Base score from IRT/Coverage/Complexity
        base = irt_manager.calculate_priority(t, coverage_data)
        # Add Usage Score (weighted heavily)
        usage = t.get("usage_score", 0) * 20 # High weight for usage
        return base + usage
        
    candidates.sort(key=score, reverse=True)
    best = candidates[0]
    
    # Sort parameters by usage for the agent's reference
    if "parameters" in best:
        best["parameters"].sort(key=lambda p: p["usage_count"], reverse=True)
    
    processed_list.append(best["file_path"] + "::" + best["method_name"])
    tool_context.session.state["processed_targets_list"] = processed_list
    
    return json.dumps(best)


# --- Tracer Logic ---

def trace_execution(code: str, target_method: dict, tool_context: ToolContext) -> str:
    """
    Executes the provided code snippet to capture a Golden Snapshot.
    Returns JSON of the GoldenSnapshot or error.
    """
    try:
        target = TargetMethod.model_validate(target_method)
    except Exception as e:
        return json.dumps({"error": f"Invalid target dict: {e}"})

    stdout_capture = io.StringIO()
    original_stdout = sys.stdout
    
    start_time = time.time()
    local_scope: Dict[str, Any] = {}
    
    # Retrieve repo_path from state to enable imports
    repo_path = tool_context.session.state.get("repo_path")
    original_sys_path = sys.path[:]
    if repo_path:
        abs_repo_path = str(Path(repo_path).resolve())
        if abs_repo_path not in sys.path:
            sys.path.insert(0, abs_repo_path)

    try:
        sys.stdout = stdout_capture
        # We wrap in a try/except block within exec to catch runtime errors
        exec(code, {}, local_scope)
        
        execution_time = time.time() - start_time
        stdout_content = stdout_capture.getvalue()
        
        captured_locals = {}
        for k, v in local_scope.items():
            if not k.startswith("__") and not callable(v) and not isinstance(v, type(sys)):
                try:
                    captured_locals[k] = repr(v)
                except:
                    captured_locals[k] = "<unrepresentable>"

        snapshot = GoldenSnapshot(
            target=target,
            valid_usage_code=code,
            stdout=stdout_content,
            return_value=captured_locals.get("result", "N/A"),
            local_vars=captured_locals,
            execution_time=execution_time
        )
        
        # Save snapshot to state for Saboteur
        tool_context.session.state["current_snapshot"] = snapshot.model_dump()
        
        return json.dumps({"status": "success", "snapshot_summary": f"Executed in {execution_time:.2f}s, Stdout len: {len(stdout_content)}"})

    except Exception as e:
        traceback_str = traceback.format_exc()
        return json.dumps({"status": "error", "message": str(e), "traceback": traceback_str})
    finally:
        sys.stdout = original_stdout
        sys.path = original_sys_path # Restore sys.path


# --- Sandbox Logic ---

def validate_mutant(mutant_code: str, tool_context: ToolContext) -> str:
    """
    Executes the mutant code to verify it behaves differently from the Golden Snapshot.
    Requires 'current_snapshot' in session state.
    """
    snapshot_data = tool_context.session.state.get("current_snapshot")
    if not snapshot_data or snapshot_data == "None":
        return json.dumps({"error": "No Golden Snapshot found in session state. Observer failed to generate one."})
    
    snapshot = GoldenSnapshot.model_validate(snapshot_data)
    
    stdout_capture = io.StringIO()
    original_stdout = sys.stdout
    
    try:
        sys.stdout = stdout_capture
        exec(mutant_code, {}, {})
        stdout_content = stdout_capture.getvalue()
        
        if stdout_content.strip() == snapshot.stdout.strip():
             return json.dumps({
                 "valid": False,
                 "reason": "Equivalent Mutant (Outputs match)",
                 "status": ValidationStatus.FAIL_ASSERTION
             })
        
        return json.dumps({
            "valid": True,
            "reason": "Divergent Output",
            "status": ValidationStatus.PASS
        })

    except SyntaxError as e:
        return json.dumps({
            "valid": False,
            "reason": f"SyntaxError: {e}",
            "status": ValidationStatus.FAIL_CRASH
        })
    except Exception as e:
        return json.dumps({
            "valid": True,
            "reason": f"Runtime Crash: {e}",
            "status": ValidationStatus.PASS
        })
    finally:
        sys.stdout = original_stdout

# --- Dedup Logic ---

def check_uniqueness(question_text: str, tool_context: ToolContext) -> str:
    """
    Checks if the proposed question is unique compared to generated benchmarks.
    Uses simple string similarity (Jaccard) on the question text.
    """
    existing_benchmarks = tool_context.session.state.get("generated_benchmarks", [])
    if not existing_benchmarks:
        return json.dumps({"unique": True, "score": 1.0})

    def jaccard_sim(str1, str2):
        a = set(str1.split())
        b = set(str2.split())
        c = a.intersection(b)
        return float(len(c)) / (len(a) + len(b) - len(c))

    max_sim = 0.0
    for b in existing_benchmarks:
        q = b.get("question", "")
        sim = jaccard_sim(question_text, q)
        if sim > max_sim:
            max_sim = sim
            
    is_unique = max_sim < 0.8
    return json.dumps({"unique": is_unique, "max_similarity": max_sim})

def save_benchmark_case(case_json: str, tool_context: ToolContext) -> str:
    """Saves the fully assembled benchmark case to the session list and a raw log file."""
    try:
        case = json.loads(case_json)
        
        # 1. Update session state (for internal logic/stats)
        current_list = tool_context.session.state.get("generated_benchmarks", [])
        tool_context.session.state["generated_benchmarks"] = current_list + [case]
        
        # 2. Persist to a raw JSONL file immediately to prevent data loss on crash/persistence fail
        # This file serves as the durable write-ahead log for benchmarks.
        raw_log_path = Path("prismatic_generated_raw.jsonl")
        with open(raw_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(case) + "\n")

        # Calculate stats
        total = len(tool_context.session.state.get("scanned_targets", []))
        processed = len(tool_context.session.state.get("processed_targets_list", []))
        generated = len(tool_context.session.state["generated_benchmarks"])
        coverage_pct = (processed / total * 100) if total > 0 else 0.0
        
        return f"Benchmark saved to {raw_log_path}. Stats: Processed {processed}/{total} targets ({coverage_pct:.1f}%). Generated {generated} benchmarks."
    except Exception as e:
        return f"Error saving case: {e}"