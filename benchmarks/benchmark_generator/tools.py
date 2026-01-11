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
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict, Counter

from google.adk.tools import ToolContext
from benchmarks.benchmark_generator.models import TargetEntity, TargetType, GoldenSnapshot, DistractorOption, ValidationStatus
from benchmarks.benchmark_generator.irt import IRTManager

# --- Scanner (Cartographer) Logic ---

def scan_repository(repo_path: str, tool_context: ToolContext, coverage_file: Optional[str] = None) -> str:
    """
    Scans the repository to build a hierarchical map of entities (Modules, Classes, Methods, Properties, Parameters).
    Acts as the 'Cartographer' and 'Strategist' by calculating usage-based priority from external statistics.
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
            except Exception: pass

    # Load Usage Stats (adk_stats.yaml)
    # This file contains the 'truth' about what is important, derived from adk-samples.
    stats_path = Path("benchmarks/adk_stats.yaml")
    usage_stats = {}
    if stats_path.exists():
        try:
            with open(stats_path, "r") as f:
                usage_stats = yaml.safe_load(f)
        except Exception:
            pass

    entities: List[TargetEntity] = []
    all_python_files = []
    ignored_dirs = {".git", ".vscode", ".gemini", "__pycache__", "env", "venv", "node_modules", "dist", "build"}
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith(".py") and not file.startswith("test_") and not file.startswith("."):
                all_python_files.append(Path(root) / file)

    # Hierarchical Definition Pass
    for full_path in all_python_files:
        try:
            relative_path = full_path.relative_to(root_dir)
            module_parts = list(relative_path.parts)
            if module_parts[-1] == "__init__.py": module_parts.pop()
            else: module_parts[-1] = module_parts[-1][:-3]
            module_fqn = ".".join(module_parts)

            # Map src.google.adk -> google.adk for stat lookup if needed
            # Assuming stats use the same package structure as repo
            
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)

            # Module Entity
            mod_stats = usage_stats.get(module_fqn, {})
            entities.append(TargetEntity(
                id=module_fqn,
                type=TargetType.MODULE,
                name=module_parts[-1],
                file_path=str(relative_path),
                usage_score=mod_stats.get("total_calls", 0),
                docstring=ast.get_docstring(tree)
            ))

            class EntityVisitor(ast.NodeVisitor):
                def __init__(self, mod_fqn, f_path):
                    self.current_class_fqn = None
                    self.mod_fqn = mod_fqn
                    self.f_path = f_path

                def visit_ClassDef(self, node):
                    if node.name.startswith("_"): return
                    
                    class_fqn = f"{self.mod_fqn}.{node.name}"
                    cls_stats = usage_stats.get(class_fqn, {})
                    entities.append(TargetEntity(
                        id=class_fqn,
                        type=TargetType.CLASS,
                        name=node.name,
                        file_path=self.f_path,
                        usage_score=cls_stats.get("total_calls", 0),
                        docstring=ast.get_docstring(node),
                        parent_id=self.mod_fqn
                    ))
                    
                    old_class = self.current_class_fqn
                    self.current_class_fqn = class_fqn
                    self.generic_visit(node)
                    self.current_class_fqn = old_class

                def visit_FunctionDef(self, node):
                    if node.name.startswith("_") and not node.name.startswith("__"):
                        return
                    
                    parent_id = self.current_class_fqn or self.mod_fqn
                    func_fqn = f"{parent_id}.{node.name}"
                    
                    complexity = node.end_lineno - node.lineno if hasattr(node, "end_lineno") else 0
                    if complexity < 3: return

                    func_stats = usage_stats.get(func_fqn, {})
                    
                    # Method Entity
                    entities.append(TargetEntity(
                        id=func_fqn,
                        type=TargetType.METHOD,
                        name=node.name,
                        file_path=self.f_path,
                        usage_score=func_stats.get("total_calls", 0),
                        complexity_score=float(complexity),
                        docstring=ast.get_docstring(node),
                        parent_id=parent_id,
                        signature=f"def {node.name}(...):" 
                    ))

                    # Parameter Entities
                    arg_stats = func_stats.get("args", {})
                    for arg in node.args.args:
                        if arg.arg == "self": continue
                        param_id = f"{func_fqn}.args.{arg.arg}"
                        p_usage = arg_stats.get(arg.arg, {}).get("count", 0)
                        
                        entities.append(TargetEntity(
                            id=param_id,
                            type=TargetType.PARAMETER,
                            name=arg.arg,
                            file_path=self.f_path,
                            usage_score=p_usage,
                            parent_id=func_fqn
                        ))

            EntityVisitor(module_fqn, str(relative_path)).visit(tree)
        except Exception: pass
    
    tool_context.session.state["scanned_targets"] = [e.model_dump() for e in entities]
    tool_context.session.state["coverage_data"] = coverage_data
    return f"Cartographer scan complete: {len(entities)} hierarchical entities mapped with external usage scores."

def get_prioritized_target(tool_context: ToolContext, target_type: Optional[str] = None, parent_id: Optional[str] = None) -> str:
    """
    Retrieves the next best target, prioritizing by Usage and Hierarchy.
    """
    targets_data = tool_context.session.state.get("scanned_targets", [])
    if not targets_data: return json.dumps({"status": "EMPTY"})
    
    processed_list = tool_context.session.state.get("processed_targets_list", [])
    processed_set = set(processed_list)
    
    # Convert back to objects for easier handling
    targets = [TargetEntity.model_validate(t) for t in targets_data]
    
    # Filter
    candidates = [t for t in targets if t.id not in processed_set]
    if target_type:
        candidates = [t for t in candidates if t.type == target_type]
    if parent_id:
        candidates = [t for t in candidates if t.parent_id == parent_id]
        
    if not candidates:
        return json.dumps({"status": "DONE"})
    
    irt_file = tool_context.session.state.get("irt_file")
    irt_manager = IRTManager(irt_file)
    coverage_data = tool_context.session.state.get("coverage_data")

    def score(t: TargetEntity):
        # Priority = Usage Only (plus IRT/Coverage/Doc bonus)
        # Disregard Complexity as requested.
        u_score = t.usage_score * 100 # Maximum weight on usage
        
        # Doc bonus to prefer documented methods if usage is tied
        doc_bonus = 10 if t.docstring else 0
        
        # IRT/Coverage weighting
        irt_p = irt_manager.calculate_priority(t.model_dump(), coverage_data)
        
        return u_score + doc_bonus + irt_p
        
    candidates.sort(key=score, reverse=True)
    best = candidates[0]
    
    # Mark as processed
    processed_list.append(best.id)
    tool_context.session.state["processed_targets_list"] = processed_list
    
    return best.model_dump_json()


# --- Tracer Logic ---

def trace_execution(code: str, target_method: dict, tool_context: ToolContext) -> str:
    """
    Executes the provided code snippet to capture a Golden Snapshot.
    """
    try:
        target = TargetEntity.model_validate(target_method)
    except Exception as e:
        return json.dumps({"error": f"Invalid target dict: {e}"})

    stdout_capture = io.StringIO()
    original_stdout = sys.stdout
    
    start_time = time.time()
    local_scope: Dict[str, Any] = {}
    
    repo_path = tool_context.session.state.get("repo_path")
    original_sys_path = sys.path[:]
    if repo_path:
        abs_repo_path = str(Path(repo_path).resolve())
        if abs_repo_path not in sys.path:
            sys.path.insert(0, abs_repo_path)

    try:
        sys.stdout = stdout_capture
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
        
        tool_context.session.state["current_snapshot"] = snapshot.model_dump()
        return json.dumps({"status": "success", "snapshot_summary": f"Executed in {execution_time:.2f}s"})

    except Exception as e:
        traceback_str = traceback.format_exc()
        return json.dumps({"status": "error", "message": str(e), "traceback": traceback_str})
    finally:
        sys.stdout = original_stdout
        sys.path = original_sys_path


# --- Sandbox Logic ---

def validate_mutant(mutant_code: str, tool_context: ToolContext) -> str:
    """
    Executes the mutant code to verify it behaves differently from the Golden Snapshot.
    """
    snapshot_data = tool_context.session.state.get("current_snapshot")
    if not snapshot_data or snapshot_data == "None":
        return json.dumps({"error": "No Golden Snapshot found in session state."})
    
    snapshot = GoldenSnapshot.model_validate(snapshot_data)
    
    stdout_capture = io.StringIO()
    original_stdout = sys.stdout
    
    try:
        sys.stdout = stdout_capture
        exec(mutant_code, {}, {})
        stdout_content = stdout_capture.getvalue()
        
        if stdout_content.strip() == snapshot.stdout.strip():
             return json.dumps({"valid": False, "reason": "Equivalent Mutant"})
        
        return json.dumps({"valid": True, "reason": "Divergent Output", "status": ValidationStatus.PASS})

    except SyntaxError as e:
        return json.dumps({"valid": False, "reason": f"SyntaxError: {e}", "status": ValidationStatus.FAIL_CRASH})
    except Exception as e:
        return json.dumps({"valid": True, "reason": f"Runtime Crash: {e}", "status": ValidationStatus.PASS})
    finally:
        sys.stdout = original_stdout

# --- Dedup Logic ---

def check_uniqueness(question_text: str, tool_context: ToolContext) -> str:
    """Checks if the proposed question is unique."""
    existing_benchmarks = tool_context.session.state.get("generated_benchmarks", [])
    if not existing_benchmarks:
        return json.dumps({"unique": True, "score": 1.0})

    def jaccard_sim(str1, str2):
        a, b = set(str1.split()), set(str2.split())
        return float(len(a.intersection(b))) / (len(a.union(b)))

    max_sim = max(jaccard_sim(question_text, b.get("question", "")) for b in existing_benchmarks)
    return json.dumps({"unique": max_sim < 0.8, "max_similarity": max_sim})

def save_benchmark_case(case_json: str, tool_context: ToolContext) -> str:
    """Saves the benchmark and returns coverage stats."""
    try:
        case = json.loads(case_json)
        current_list = tool_context.session.state.get("generated_benchmarks", [])
        tool_context.session.state["generated_benchmarks"] = current_list + [case]
        
        raw_log_path = Path("prismatic_generated_raw.jsonl")
        with open(raw_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(case) + "\n")

        total = len(tool_context.session.state.get("scanned_targets", []))
        processed = len(tool_context.session.state.get("processed_targets_list", []))
        generated = len(tool_context.session.state["generated_benchmarks"])
        coverage_pct = (processed / total * 100) if total > 0 else 0.0
        
        return f"Benchmark saved to {raw_log_path}. Stats: Processed {processed}/{total} targets ({coverage_pct:.1f}%)."
    except Exception as e:
        return f"Error saving case: {e}"