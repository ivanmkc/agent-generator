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
from collections import defaultdict, Counter, deque

from google.adk.tools import ToolContext
from benchmarks.benchmark_generator.models import TargetEntity, TargetType, GoldenSnapshot, DistractorOption, ValidationStatus, ContextNode
from benchmarks.benchmark_generator.irt import IRTManager

# --- Scanner (Cartographer) Logic ---

def scan_repository(repo_path: str, tool_context: ToolContext, coverage_file: Optional[str] = None, namespace: Optional[str] = None) -> str:
    """
    Scans the repository to build a hierarchical map of entities.
    Acts as the 'Cartographer' and 'Strategist' by calculating usage-based priority from external statistics.
    Filters entities to stay within the specified namespace if provided.
    """
    root_dir = Path(repo_path).resolve()
    if not root_dir.exists():
        return json.dumps({"error": f"Path {repo_path} (resolved to {root_dir}) does not exist."})

    # Retrieve namespace from state if not provided (CLI override)
    if not namespace:
        namespace = tool_context.session.state.get("target_namespace")

    # Load coverage data
    if not coverage_file:
        coverage_file = tool_context.session.state.get("coverage_file_path")
    coverage_data = None
    if coverage_file and Path(coverage_file).exists():
        try:
            coverage_json = json.loads(Path(coverage_file).read_text())
            coverage_data = coverage_json.get("files", {})
        except Exception: pass

    # Load Usage Stats (adk_stats.yaml)
    # Allow override via state for testing
    stats_file_override = tool_context.session.state.get("stats_file_path")
    stats_path = Path(stats_file_override) if stats_file_override else Path("benchmarks/adk_stats.yaml")
    
    usage_stats = {}
    if stats_path.exists():
        try:
            with open(stats_path, "r") as f:
                usage_stats = yaml.safe_load(f)
        except Exception: pass

    # Load Co-occurrence Data (default or override)
    coocc_file_override = tool_context.session.state.get("cooccurrence_file")
    coocc_path = Path(coocc_file_override) if coocc_file_override else Path("benchmarks/adk_cooccurrence.json")
    
    cooccurrence_data = {}
    if coocc_path.exists():
        try:
            with open(coocc_path, "r") as f:
                cooccurrence_data = json.load(f)
        except Exception: pass

    entities: List[TargetEntity] = []
    # Store raw structure map for context expansion
    structure_map = {}
    alias_map = {}
    
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
            if module_fqn.startswith("src."): module_fqn = module_fqn[4:]

            if namespace and not module_fqn.startswith(namespace):
                continue

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)

            # Record Module in Structure Map
            structure_map[module_fqn] = {
                "type": "Module", 
                "name": module_parts[-1] if module_parts else "root", 
                "children": [], "params": {}, "props": []
            }
            
            # Module Entity for Ranking
            mod_stats = usage_stats.get(module_fqn, {})
            entities.append(TargetEntity(
                id=module_fqn,
                type=TargetType.MODULE,
                name=module_parts[-1] if module_parts else "root",
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
                    
                    # Structure Map
                    structure_map[class_fqn] = {
                        "type": "Class", "name": node.name, "children": [], "params": {}, "props": []
                    }
                    structure_map[self.mod_fqn]["children"].append(class_fqn)
                    
                    # Entity
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
                    if node.name.startswith("_") and node.name != "__init__": return
                    parent_fqn = self.current_class_fqn or self.mod_fqn
                    func_fqn = f"{parent_fqn}.{node.name}"
                    
                    params = {arg.arg: (ast.unparse(arg.annotation) if arg.annotation else "Any") for arg in node.args.args if arg.arg != "self"}
                    
                    # Structure Map
                    structure_map[func_fqn] = {
                        "type": "Method", "name": node.name, "children": [], "params": params, "props": []
                    }
                    if parent_fqn in structure_map:
                        structure_map[parent_fqn]["children"].append(func_fqn)

                    complexity = node.end_lineno - node.lineno if hasattr(node, "end_lineno") else 0
                    if complexity < 3: return
                    
                    # Entity
                    func_stats = usage_stats.get(func_fqn, {})
                    entities.append(TargetEntity(
                        id=func_fqn,
                        type=TargetType.METHOD,
                        name=node.name,
                        file_path=self.f_path,
                        usage_score=func_stats.get("total_calls", 0),
                        complexity_score=float(complexity),
                        docstring=ast.get_docstring(node),
                        parent_id=parent_fqn,
                        signature=f"def {node.name}(...):"
                    ))
                
                def visit_Assign(self, node):
                    if self.current_class_fqn:
                        for target in node.targets:
                            if isinstance(target, ast.Name) and not target.id.startswith("_"):
                                structure_map[self.current_class_fqn]["props"].append(target.id)
                
                def visit_ImportFrom(self, node):
                    if relative_path.name == "__init__.py":
                        module = node.module or ""
                        if node.level > 0:
                            base = self.mod_fqn.split(".")
                            canonical_base = ".".join(base[:len(base) - (node.level - 1)])
                            canonical_mod = f"{canonical_base}.{module}" if module else canonical_base
                        else:
                            canonical_mod = module
                        for alias in node.names:
                            alias_fqn = f"{self.mod_fqn}.{alias.asname or alias.name}"
                            canonical_fqn = f"{canonical_mod}.{alias.name}"
                            alias_map[alias_fqn] = canonical_fqn

            EntityVisitor(module_fqn, str(relative_path)).visit(tree)
        except Exception: pass
    
    # Save scanned data to session state for the Strategist
    tool_context.session.state["scanned_targets"] = [e.model_dump() for e in entities]
    tool_context.session.state["structure_map"] = structure_map
    tool_context.session.state["alias_map"] = alias_map
    tool_context.session.state["usage_stats"] = usage_stats
    tool_context.session.state["cooccurrence_data"] = cooccurrence_data
    tool_context.session.state["coverage_data"] = coverage_data
    
    return f"Cartographer scan complete: {len(entities)} hierarchical entities mapped. Structure map size: {len(structure_map)}."

def list_prioritized_targets(tool_context: ToolContext, limit: int = 20) -> str:
    """
    Returns a prioritized list of target IDs and their usage scores.
    The Auditor should use this to pick the next target.
    """
    targets_data = tool_context.session.state.get("scanned_targets", [])
    if not targets_data: return "No targets scanned. Call scan_repository first."
    
    processed_list = tool_context.session.state.get("processed_targets_list", [])
    processed_set = set(processed_list)
    
    targets = [TargetEntity.model_validate(t) for t in targets_data]
    candidates = [t for t in targets if t.id not in processed_set]
    
    if not candidates: return "DONE"
    
    irt_file = tool_context.session.state.get("irt_file")
    irt_manager = IRTManager(irt_file)
    coverage_data = tool_context.session.state.get("coverage_data")

    def score(t: TargetEntity):
        u_score = t.usage_score * 100 
        irt_p = irt_manager.calculate_priority(t.model_dump(), coverage_data)
        return u_score + irt_p
        
    candidates.sort(key=score, reverse=True)
    
    results = []
    for t in candidates[:limit]:
        results.append({"id": t.id, "usage": t.usage_score, "type": t.type})
        
    return json.dumps(results)

def select_target(target_id: str, tool_context: ToolContext) -> str:
    """
    Selects a specific target, performs context expansion, and prepares it for the Observer.
    Returns the full TargetEntity JSON for the Auditor to review.
    """
    targets_data = tool_context.session.state.get("scanned_targets", [])
    target_dict = next((t for t in targets_data if t["id"] == target_id), None)
    
    if not target_dict:
        return f"Error: Target {target_id} not found."
    
    best = TargetEntity.model_validate(target_dict)
    
    # --- Context Expansion (BFS Chain) ---
    structure_map = tool_context.session.state.get("structure_map", {})
    alias_map = tool_context.session.state.get("alias_map", {})
    usage_stats = tool_context.session.state.get("usage_stats", {})
    cooccurrence_data = tool_context.session.state.get("cooccurrence_data", {})
    associations = cooccurrence_data.get("associations", [])
    
    def resolve_fqn(name):
        if name in structure_map: return name
        if name in alias_map: return resolve_fqn(alias_map[name])
        return name

    if associations:
        prob_map = defaultdict(dict)
        for a in associations:
            prob_map[a["context"]][a["target"]] = a["probability"]
        
        parts = best.id.split(".")
        start_node = None
        for i in range(len(parts), 0, -1):
            sub = ".".join(parts[:i])
            # Check if this node exists in our probability map or structure map
            if sub in prob_map or sub in structure_map:
                start_node = sub
                break
        
        # Fallback if ID is a method but structure map only has class/module keys
        if not start_node:
            start_node = best.id

        if start_node:
            queue = deque([(start_node, 1.0)])
            final_probs = {start_node: 1.0}
            threshold = 0.05
            
            # Robust Chain-Rule BFS (from adk_chain_prob.py)
            while queue:
                curr, p = queue.popleft()
                for neighbor, cond_p in prob_map.get(curr, {}).items():
                    new_p = p * cond_p
                    if new_p >= threshold and new_p > final_probs.get(neighbor, 0.0):
                        final_probs[neighbor] = new_p
                        queue.append((neighbor, new_p))
            
            context_nodes = []
            processed_context = set()
            
            def build_context_list(node_fqn, prob, parent=None):
                if node_fqn in processed_context: return
                processed_context.add(node_fqn)
                
                canonical = resolve_fqn(node_fqn)
                # If resolve_fqn failed or structure map is incomplete, try fuzzy matching
                if canonical not in structure_map:
                    # Try to find a match in structure map keys
                    last = node_fqn.split(".")[-1]
                    candidates = [k for k in structure_map.keys() if k.endswith(f".{last}") or k == last]
                    if candidates:
                        canonical = max(candidates, key=lambda x: len(os.path.commonprefix([x, node_fqn])))

                node_def = structure_map.get(canonical)
                context_nodes.append(ContextNode(id=canonical, type=node_def["type"] if node_def else "Unknown", probability=prob, usage=usage_stats.get(canonical, {}).get("total_calls", 0), parent_id=parent))
                
                # Recursively add children (like __init__) if it's a class
                if node_def and node_def["type"] == "Class":
                     for child_fqn in node_def.get("children", []):
                         child_def = structure_map.get(child_fqn)
                         if child_def and child_def["type"] == "Method" and child_def["name"] == "__init__":
                             build_context_list(child_fqn, 1.0, parent=canonical)

            for node_name, prob in sorted(final_probs.items(), key=lambda x: x[1], reverse=True):
                # Only include nodes that are NOT the start node itself (redundant)
                # unless we really want its definition in the context list too?
                # Usually best.source_code covers the target. Context covers dependencies.
                if node_name != start_node:
                    build_context_list(node_name, prob)
            
            best.associated_context = context_nodes

    # Populate source code
    if best.file_path:
        repo_path = tool_context.session.state.get("repo_path", ".")
        full_path = Path(repo_path) / best.file_path
        if full_path.exists():
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content)
                # Simple logic to find the node by name and type
                for node in ast.walk(tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == best.name:
                        # For methods, check parent FQN if possible
                        node_fqn = best.id # Assume ID is FQN
                        # This is a bit naive but works for top-level classes and functions
                        best.source_code = ast.get_source_segment(content, node)
                        break
            except Exception: pass

    # Mark as processed
    processed_list = tool_context.session.state.get("processed_targets_list", [])
    processed_list.append(best.id)
    tool_context.session.state["processed_targets_list"] = processed_list
    
    # Save to state for Auditor to "see"
    res_json = best.model_dump_json()
    tool_context.session.state["current_target_json"] = res_json
    return res_json



# --- Tracer Logic ---

def trace_execution(code: str, target_method: dict, tool_context: ToolContext) -> str:
    """Executes the provided code snippet to capture a Golden Snapshot."""
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
    original_modules = sys.modules.copy() # Backup modules
    
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
        # Restore sys.modules to prevent pollution from exec()
        # We only restore keys that were present; new modules are left (optional) or we can strict restore.
        # Strict restore is safer for preventing 'MagicMock' replacements of real modules.
        sys.modules.clear()
        sys.modules.update(original_modules)

# --- Sandbox Logic ---

def validate_mutant(mutant_code: str, tool_context: ToolContext) -> str:
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
    existing_benchmarks = tool_context.session.state.get("generated_benchmarks", [])
    if not existing_benchmarks:
        return json.dumps({"unique": True, "score": 1.0})
    def jaccard_sim(str1, str2):
        a, b = set(str1.split()), set(str2.split())
        return float(len(a.intersection(b))) / (len(a.union(b)))
    max_sim = max(jaccard_sim(question_text, b.get("question", "")) for b in existing_benchmarks)
    return json.dumps({"unique": max_sim < 0.8, "max_similarity": max_sim})

def save_benchmark_case(case_json: str, tool_context: ToolContext) -> str:
    try:
        case = json.loads(case_json)
        
        # Schema Normalization: Map Prismatic (flat) schema to Standard MC (dict) schema
        normalized_case = {}
        
        # 1. Question
        if "question" in case:
            normalized_case["question"] = case["question"]
        elif "q" in case:
            normalized_case["question"] = case["q"]
        else:
             return json.dumps({"error": "Missing 'question' or 'q' field."})

        # 2. Options
        options = {}
        if "options" in case and isinstance(case["options"], dict):
             options = case["options"]
        else:
            # Flattened keys
            if "a" in case: options["A"] = str(case["a"])
            if "b" in case: options["B"] = str(case["b"])
            if "c" in case: options["C"] = str(case["c"])
            if "d" in case: options["D"] = str(case["d"])
            
            # Or list
            if not options and "options" in case and isinstance(case["options"], list):
                letters = ["A", "B", "C", "D"]
                for i, opt in enumerate(case["options"][:4]):
                    options[letters[i]] = str(opt)
        
        if not options:
             return json.dumps({"error": "Missing options (a/b/c/d or options dict/list)."})
        
        normalized_case["options"] = options

        # 3. Correct Answer
        mapping = {0: "A", 1: "B", 2: "C", 3: "D", "0": "A", "1": "B", "2": "C", "3": "D"}
        if "correct_answer" in case:
             normalized_case["correct_answer"] = case["correct_answer"]
        elif "correct_idx" in case:
             val = case["correct_idx"]
             if val in mapping:
                 normalized_case["correct_answer"] = mapping[val]
             else:
                 # Try to interpret as integer
                 try:
                     normalized_case["correct_answer"] = mapping[int(val)]
                 except:
                     pass
        
        if "correct_answer" not in normalized_case:
             # Maybe it's the text of the answer? or the letter itself?
             pass 

        # 4. Explanation
        if "explanation" in case:
            normalized_case["explanation"] = case["explanation"]
        elif "context" in case:
             normalized_case["explanation"] = case["context"]

        normalized_case["benchmark_type"] = "multiple_choice"

        # Update Session State
        current_list = tool_context.session.state.get("generated_benchmarks", [])
        tool_context.session.state["generated_benchmarks"] = current_list + [normalized_case]
        
        # JSONL Log (Robust) - Save Normalized
        raw_log_path = Path("prismatic_generated_raw.jsonl")
        with open(raw_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(normalized_case) + "\n")
            
        # YAML Partial Log (On-the-fly) - Strict Schema
        output_dir = tool_context.session.state.get("output_dir")
        if output_dir:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            
            # 1. Save Benchmark Case to Partial YAML
            yaml_path = out_path / "benchmark_partial.yaml"
            first_write = not yaml_path.exists() or yaml_path.stat().st_size == 0
            
            # Create a clean dict for YAML to avoid Pydantic validation errors later
            yaml_case = {
                "question": normalized_case.get("question"),
                "options": normalized_case.get("options"),
                "correct_answer": normalized_case.get("correct_answer"),
                "explanation": normalized_case.get("explanation"),
                "benchmark_type": "multiple_choice"
            }
            
            with open(yaml_path, "a", encoding="utf-8") as f:
                if first_write:
                    f.write("benchmarks:\n")
                yaml_str = yaml.safe_dump([yaml_case], sort_keys=False)
                f.write(yaml_str)

            # 2. Save Golden Snapshot to Corpus (reusable valid code)
            snapshot_data = tool_context.session.state.get("current_snapshot")
            if snapshot_data and snapshot_data != "None":
                if isinstance(snapshot_data, str):
                    snapshot_data = json.loads(snapshot_data)
                
                corpus_entry = {
                    "target_id": snapshot_data.get("target", {}).get("id", "unknown"),
                    "code": snapshot_data.get("valid_usage_code", ""),
                    "stdout": snapshot_data.get("stdout", ""),
                    "timestamp": time.time()
                }
                
                corpus_path = out_path / "valid_usage_corpus.jsonl"
                with open(corpus_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(corpus_entry) + "\n")

        total = len(tool_context.session.state.get("scanned_targets", []))
        processed = len(tool_context.session.state.get("processed_targets_list", []))
        coverage_pct = (processed / total * 100) if total > 0 else 0.0
        return f"Benchmark saved to {raw_log_path} and {yaml_path if output_dir else 'memory'}. Stats: Processed {processed}/{total} targets ({coverage_pct:.1f}%)."
    except Exception as e:
        return f"Error saving case: {e}"