"""
AST-based repository scanner.

This module provides the `scan_repository` function, which walks a Python codebase,
parses files into ASTs, and extracts structural information (classes, methods,
docstrings, complexity) into `TargetEntity` objects.
"""

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

"""Tools for the Agentic Benchmark Generator agents."""

import ast
import os
import sys
import yaml
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict

from benchmarks.generator.benchmark_generator.models import TargetEntity, TargetType

# --- Scanner (Cartographer) Logic ---


def scan_repository(
    repo_path: str,
    coverage_file: Optional[str] = None,
    namespace: Optional[str] = None,
    root_namespace_prefix: Optional[str] = None,
    usage_stats: Optional[Dict] = None,
    cooccurrence: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Scans the repository to build a hierarchical map of entities.
    Calculates usage-based priority from external statistics.
    Filters entities to stay within the specified namespace if provided.

    Features:
    - Resolves type hints to Fully Qualified Names (FQNs) via import analysis.
    - Handles string forward references and local class definitions.

    Returns:
        Dict containing:
        - scanned_targets: List[TargetEntity]
        - structure_map: Dict
        - usage_stats: Dict
        - alias_map: Dict
    """
    root_dir = Path(repo_path).resolve()
    if not root_dir.exists():
        return {"error": f"Path {repo_path} (resolved to {root_dir}) does not exist."}

    # Load coverage data
    coverage_data = None
    if coverage_file and Path(coverage_file).exists():
        try:
            coverage_json = json.loads(Path(coverage_file).read_text())
            coverage_data = coverage_json.get("files", {})
        except Exception:
            pass

    # Load Usage Stats if not provided
    if usage_stats is None:
        usage_stats = {}
        # Default fallback (can be improved or removed if caller must provide)
        stats_path = Path("benchmarks/adk_stats.yaml")
        if stats_path.exists():
            try:
                with open(stats_path, "r") as f:
                    usage_stats = yaml.safe_load(f)
            except Exception:
                pass

    # Load Co-occurrence Data if not provided
    if cooccurrence is None:
        cooccurrence = {}
        coocc_path = Path("benchmarks/adk_cooccurrence.yaml")
        if coocc_path.exists():
            try:
                with open(coocc_path, "r") as f:
                    cooccurrence = yaml.safe_load(f)
            except Exception:
                pass

    cooccurrence_data = {}
    if coocc_path.exists():
        try:
            with open(coocc_path, "r") as f:
                cooccurrence_data = yaml.safe_load(f)
        except Exception:
            pass

    entities: List[TargetEntity] = []
    # Store raw structure map for context expansion
    structure_map = {}
    alias_map = {}

    all_python_files = []
    ignored_dirs = {
        ".git",
        ".vscode",
        ".gemini",
        "__pycache__",
        "env",
        "venv",
        "node_modules",
        "dist",
        "build",
    }

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if (
                file.endswith(".py")
                and not file.startswith("test_")
                and not file.startswith(".")
            ):
                all_python_files.append(Path(root) / file)

    # Hierarchical Definition Pass
    for full_path in all_python_files:
        _scan_file_single(
            full_path,
            root_dir,
            root_namespace_prefix,
            namespace,
            usage_stats,
            structure_map,
            entities,
            alias_map,
        )

    # --- Post-Scan Usage Correction (Runtime Identity) ---
    # Resolve aliases by checking if objects are identical in memory.

    print("[DEBUG] Building Runtime Usage Map...")
    runtime_usage_map = {}  # {id(obj): count}

    # Pre-load usage stats into memory map
    sys.path.insert(0, str(root_dir))  # Ensure we can import
    for fqn, stats in usage_stats.items():
        try:
            # Import module and get object
            parts = fqn.split(".")
            module_name = ".".join(parts[:-1])
            obj_name = parts[-1]
            module = __import__(module_name, fromlist=[obj_name])
            obj = getattr(module, obj_name)
            obj_id = id(obj)
            current_count = runtime_usage_map.get(obj_id, 0)
            runtime_usage_map[obj_id] = current_count + stats.get("total_calls", 0)
        except Exception:
            pass  # Ignore import errors for stats keys

    # Fix Entities
    print(f"[DEBUG] Correcting {len(entities)} entities using runtime identity...")
    for entity in entities:
        if entity.usage_score == 0:
            try:
                # Import entity
                parts = entity.id.split(".")
                # Handle module vs class/func
                if entity.type == TargetType.MODULE:
                    obj = __import__(entity.id, fromlist=["*"])
                else:
                    module_name = ".".join(parts[:-1])
                    obj_name = parts[-1]
                    module = __import__(module_name, fromlist=[obj_name])
                    obj = getattr(module, obj_name)

                # Check identity
                if id(obj) in runtime_usage_map:
                    calls = runtime_usage_map[id(obj)]
                    if calls > 0:
                        print(
                            f"[DEBUG] Correcting usage for {entity.id}: 0 -> {calls} (Runtime Identity Match)"
                        )
                        entity.usage_score = calls
            except Exception:
                pass  # Fail silently if we can't import/find (e.g. syntax errors in file)

    # Remove from sys.path to be clean
    if str(root_dir) in sys.path:
        sys.path.remove(str(root_dir))

    # tool_context assignments removed
    
    return {
        "scanned_targets": [e.model_dump() for e in entities],
        "structure_map": structure_map,
        "alias_map": alias_map,
        "usage_stats": usage_stats,
        "cooccurrence_data": cooccurrence_data,
        "coverage_data": coverage_data
    }

def _scan_file_single(
    full_path: Path,
    root_dir: Path,
    root_namespace_prefix: Optional[str],
    namespace: Optional[str],
    usage_stats: Dict[str, Any],
    structure_map: Dict[str, Any],
    entities: List[TargetEntity],
    alias_map: Dict[str, str],
):
    try:
        if full_path.is_absolute():
            # Try to make it relative to root_dir if possible, else just use name
            try:
                relative_path = full_path.relative_to(root_dir)
            except ValueError:
                # If file is not in root_dir (external dependency), use full path or special handling
                # For external deps, we might be passed a different root_dir or we just want relative parts
                # If we are scanning site-packages, we usually set root_dir to site-packages root
                relative_path = full_path
        else:
            relative_path = full_path

        module_parts = list(relative_path.parts)
        if module_parts[-1] == "__init__.py":
            module_parts.pop()
        else:
            module_parts[-1] = module_parts[-1][:-3]
        
        # Handle case where file is outside root (e.g. traversal)
        # If relative_path is absolute, parts will start with root. 
        # But we really want the package structure.
        # If we are scanning a file in tmp_deps/google/genai/client.py
        # and root_dir is tmp_deps
        # relative is google/genai/client.py
        # module_fqn is google.genai.client
        
        module_fqn = ".".join(module_parts)
        if module_fqn.startswith("src."):
            module_fqn = module_fqn[4:]

        if root_namespace_prefix:
            if module_fqn:
                module_fqn = f"{root_namespace_prefix}.{module_fqn}"
            else:
                module_fqn = root_namespace_prefix

        if namespace and not module_fqn.startswith(namespace):
            return

        # Public API Filter: Skip modules with private components
        if any(part.startswith("_") for part in module_fqn.split(".")):
            return

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)

        # Record Module in Structure Map
        structure_map[module_fqn] = {
            "type": "Module",
            "name": module_parts[-1] if module_parts else "root",
            "children": [],
            "params": {},
            "props": [],
        }

        # Module Entity
        mod_stats = usage_stats.get(module_fqn, {})
        entities.append(
            TargetEntity(
                id=module_fqn,
                type=TargetType.MODULE,
                name=module_parts[-1] if module_parts else "root",
                file_path=str(relative_path),
                usage_score=mod_stats.get("total_calls", 0),
                docstring=ast.get_docstring(tree),
            )
        )

        visitor = EntityVisitor(module_fqn, str(relative_path), structure_map, entities, usage_stats, alias_map)
        visitor.collect_metadata(tree)
        visitor.visit(tree)
    except Exception as e:
        # logging.warning(f"Failed to scan {full_path}: {e}")
        pass

class EntityVisitor(ast.NodeVisitor):

    def __init__(self, mod_fqn, f_path, structure_map, entities, usage_stats, alias_map):
        self.current_class_fqn = None
        self.in_function = False
        self.mod_fqn = mod_fqn
        self.f_path = f_path
        self.imports = {}
        self.local_names = set()
        self.exported_names = None
        
        self.structure_map = structure_map
        self.entities = entities
        self.usage_stats = usage_stats
        self.alias_map = alias_map

    def collect_metadata(self, node):
        """Pre-scans top-level nodes for __all__ and locally defined names."""
        if not hasattr(node, "body"):
            return
        for child in node.body:
            if isinstance(
                child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                self.local_names.add(child.name)
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        self.local_names.add(target.id)
                        # Detect __all__ = [...]
                        if target.id == "__all__" and isinstance(child.value, (ast.List, ast.Tuple)):
                            self.exported_names = set()
                            for elt in child.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    self.exported_names.add(elt.value)
            elif isinstance(child, ast.Expr) and isinstance(child.value, ast.Call):
                # Detect __all__.extend([...]) or __all__.append("...")
                call = child.value
                if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == "__all__":
                    if self.exported_names is None:
                        self.exported_names = set()
                    
                    if call.func.attr == "extend" and len(call.args) == 1:
                        if isinstance(call.args[0], (ast.List, ast.Tuple)):
                            for elt in call.args[0].elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    self.exported_names.add(elt.value)
                    elif call.func.attr == "append" and len(call.args) == 1:
                        if isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
                            self.exported_names.add(call.args[0].value)
            elif isinstance(child, ast.AnnAssign):
                if isinstance(child.target, ast.Name):
                    self.local_names.add(child.target.id)

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        # Resolve relative imports
        if node.level > 0:
            parts = self.mod_fqn.split(".")
            
            # Fix for __init__.py: mod_fqn IS the package.
            path_name = Path(self.f_path).name # Need to check if it is init via path string
            is_init = path_name == "__init__.py"

            if is_init:
                cutoff = len(parts) - (node.level - 1)
            else:
                cutoff = len(parts) - node.level
                
            if cutoff < 0: cutoff = 0
            prefix = ".".join(parts[:cutoff])
                
            if prefix:
                module = f"{prefix}.{module}" if module else prefix

        for alias in node.names:
            alias_name = alias.asname or alias.name
            if alias.name == "*":
                continue
            self.imports[alias_name] = (
                f"{module}.{alias.name}" if module else alias.name
            )

        # Also populate alias_map for the scanner's structural needs if in __init__
        path_name = Path(self.f_path).name
        if path_name == "__init__.py":
            canonical_mod = module
            for alias in node.names:
                alias_name = alias.asname or alias.name
                
                # Filter: If __all__ exists, only record if alias_name is in it.
                if self.exported_names is not None and alias_name not in self.exported_names:
                    continue

                alias_fqn = f"{self.mod_fqn}.{alias_name}"
                canonical_fqn = f"{canonical_mod}.{alias.name}"
                
                if (
                    canonical_fqn in self.structure_map
                    and self.structure_map[canonical_fqn]["type"] != "Module"
                    and (alias_fqn not in self.structure_map or self.structure_map[alias_fqn]["type"] != "Module")
                ):
                    self.alias_map[alias_fqn] = canonical_fqn

        self.generic_visit(node)

    def resolve_annotation(self, node):
        if node is None:
            return "Any"

        try:
            if isinstance(node, ast.Name):
                if node.id in self.imports:
                    return self.imports[node.id]
                if node.id in self.local_names:
                    return f"{self.mod_fqn}.{node.id}"
                return node.id

            elif isinstance(node, ast.Attribute):
                value_str = self.resolve_annotation(node.value)
                return f"{value_str}.{node.attr}"

            elif isinstance(node, ast.Subscript):
                value_str = self.resolve_annotation(node.value)
                slice_str = "Any"
                if hasattr(node, "slice"):
                    slice_node = node.slice
                    if isinstance(slice_node, ast.Tuple):
                        slice_str = ", ".join(
                            [
                                self.resolve_annotation(elt)
                                for elt in slice_node.elts
                            ]
                        )
                    else:
                        slice_str = self.resolve_annotation(slice_node)
                return f"{value_str}[{slice_str}]"

            elif isinstance(node, ast.Tuple):
                return ", ".join(
                    [self.resolve_annotation(elt) for elt in node.elts]
                )

            elif isinstance(node, ast.Constant):
                if isinstance(node.value, str):
                    try:
                        parsed = ast.parse(node.value, mode="eval")
                        return self.resolve_annotation(parsed.body)
                    except:
                        return node.value
                return str(node.value)

            return ast.unparse(node)
        except:
            try:
                return ast.unparse(node)
            except:
                return "Any"

    def visit_ClassDef(self, node):
        if node.name.startswith("_") and node.name != "_run_async_impl":
            return
        class_fqn = f"{self.mod_fqn}.{node.name}"

        # Extract Bases
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(ast.unparse(base))

        # Extract Decorators
        decorators = []
        for decorator in node.decorator_list:
            try:
                if isinstance(decorator, ast.Name):
                    decorators.append(decorator.id)
                elif isinstance(decorator, ast.Attribute):
                    decorators.append(ast.unparse(decorator))
                elif isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Name):
                        decorators.append(decorator.func.id)
                    elif isinstance(decorator.func, ast.Attribute):
                        decorators.append(ast.unparse(decorator.func))
            except:
                pass

        # Structure Map
        self.structure_map[class_fqn] = {
            "type": "Class",
            "name": node.name,
            "children": [],
            "params": {},
            "props": [],
            "bases": bases,
            "decorators": decorators,
        }
        self.structure_map[self.mod_fqn]["children"].append(class_fqn)

        # Entity
        cls_stats = self.usage_stats.get(class_fqn, {})
        self.entities.append(
            TargetEntity(
                id=class_fqn,
                type=TargetType.CLASS,
                name=node.name,
                file_path=self.f_path,
                usage_score=cls_stats.get("total_calls", 0),
                docstring=ast.get_docstring(node),
                parent_id=self.mod_fqn,
            )
        )

        old_class = self.current_class_fqn
        self.current_class_fqn = class_fqn

        # -- Property Docstring Extraction --
        body = node.body
        for i, child in enumerate(body):
            prop_name = None
            prop_type = "Any"

            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(
                        target, ast.Name
                    ) and not target.id.startswith("_"):
                        prop_name = target.id
                        # Infer type (simple)
                        if isinstance(child.value, ast.Constant):
                            prop_type = type(child.value.value).__name__
                        elif isinstance(child.value, ast.Call):
                            if isinstance(child.value.func, ast.Name):
                                # Resolve function name
                                prop_type = self.imports.get(
                                    child.value.func.id, child.value.func.id
                                )
                            elif isinstance(
                                child.value.func, ast.Attribute
                            ):
                                # Resolve attribute chain
                                prop_type = self.resolve_annotation(
                                    child.value.func
                                )
                        break
            elif isinstance(child, ast.AnnAssign):
                if isinstance(
                    child.target, ast.Name
                ) and not child.target.id.startswith("_"):
                    prop_name = child.target.id
                    prop_type = self.resolve_annotation(child.annotation)

            if prop_name:
                # Look ahead for docstring
                doc = None
                if i + 1 < len(body):
                    next_node = body[i + 1]
                    if (
                        isinstance(next_node, ast.Expr)
                        and isinstance(next_node.value, ast.Constant)
                        and isinstance(next_node.value.value, str)
                    ):
                        doc = next_node.value.value

                self._add_prop(prop_name, prop_type, doc)

        self.generic_visit(node)
        self.current_class_fqn = old_class

    def _visit_any_function(self, node):
        old_in_func = self.in_function
        self.in_function = True

        is_public = (
            not node.name.startswith("_")
            or node.name == "_run_async_impl"
            or node.name == "__init__"
        )
        if is_public:
            parent_fqn = self.current_class_fqn or self.mod_fqn
            func_fqn = f"{parent_fqn}.{node.name}"

            params = {
                arg.arg: self.resolve_annotation(arg.annotation)
                for arg in node.args.args
                if arg.arg != "self"
            }
            doc = ast.get_docstring(node)

            # Reconstruct Full Signature with Resolved Types
            args_list = []

            for arg in node.args.args:
                arg_str = arg.arg
                if arg.annotation:
                    arg_str += (
                        f": {self.resolve_annotation(arg.annotation)}"
                    )
                args_list.append(arg_str)

            if node.args.kwonlyargs:
                args_list.append("*")
                for arg, default in zip(
                    node.args.kwonlyargs, node.args.kw_defaults
                ):
                    arg_str = arg.arg
                    if arg.annotation:
                        arg_str += (
                            f": {self.resolve_annotation(arg.annotation)}"
                        )
                    if default:
                        try:
                            arg_str += f"={ast.unparse(default)}"
                        except:
                            arg_str += "=..."
                    args_list.append(arg_str)

            ret_str = ""
            if node.returns:
                ret_str = f" -> {self.resolve_annotation(node.returns)}"

            full_sig = f"def {node.name}({', '.join(args_list)}){ret_str}:"

            decorators = [self.resolve_annotation(d) for d in node.decorator_list]

            self.structure_map[func_fqn] = {
                "type": "Method",
                "name": node.name,
                "children": [],
                "params": params,
                "props": [],
                "decorators": decorators,
                "docstring": doc,
                "signature": full_sig,
            }
            if parent_fqn in self.structure_map:
                self.structure_map[parent_fqn]["children"].append(func_fqn)

            if node.end_lineno - node.lineno >= 3:
                func_stats = self.usage_stats.get(func_fqn, {})
                self.entities.append(
                    TargetEntity(
                        id=func_fqn,
                        type=TargetType.METHOD,
                        name=node.name,
                        file_path=self.f_path,
                        usage_score=func_stats.get("total_calls", 0),
                        docstring=doc,
                        parent_id=parent_fqn,
                        signature=f"def {node.name}(...):",
                        signature_full=full_sig,
                    )
                )

        # CRITICAL CHANGE FOR "USAGE-BASED DISCOVERY":
        # We do NOT treat function bodies as sources of *public* dependencies.
        # However, `EntityVisitor` is mainly recording structure.
        # If we visit the body, we might resolve usage inside?
        # Scan Repository logic doesn't really resolve usage, it just maps structure.
        # Wait, `resolve_annotation` calls `self.imports`.
        # The recursion `self.generic_visit(node)` is what traverses expected children.
        # If we want to strictly ignore bodies for INDEXING purposes, we are fine.
        # But if we want to ignore bodies for DISCOVERY purposes (in Ranker),
        # we need to skip `generic_visit` here?
        # NO. `EntityVisitor` builds the graph of *defined* entities.
        # It doesn't determine what gets *crawled*.
        # The `ranker` determines what gets crawled.
        # Standard valid visitation.
        
        # BUT: The plan said "Do NOT analyze functionality inside function bodies."
        # This refers to the Discovery Step (in Ranker), not the Indexing Step (here).
        # Actually, here we are Indexing. 
        # If we index the body, we index nested functions/classes.
        # Do we want nested classes/functions in the Public API index? 
        # Probably not.
        # So we should validly SKIP `generic_visit` inside functions for *Public API Indexing*.
        # This matches the user request.
        # "Strict Public API Signatures".
        
        # self.generic_visit(node) -> Visits body.
        # If we remove it or limit it:
        # We lose local classes/functions (good).
        # We lose assignments in body? (Assigns in functions are local vars -> ignore).
        # We keep params/returns (already processed).
        # So YES, removing `generic_visit(node)` inside `_visit_any_function` 
        # is correct for Public API only indexing.
        
        # Verify:
        pass # self.generic_visit(node) REMOVED
        self.in_function = old_in_func

    def visit_FunctionDef(self, node):
        self._visit_any_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_any_function(node)

    def _is_init_excluded_field(self, node):
        try:
            if isinstance(node, ast.Call):
                is_field = False
                if isinstance(node.func, ast.Name) and node.func.id in (
                    "Field",
                    "field",
                ):
                    is_field = True
                elif isinstance(
                    node.func, ast.Attribute
                ) and node.func.attr in ("Field", "field"):
                    is_field = True

                if is_field:
                    for kw in node.keywords:
                        if kw.arg == "init":
                            if (
                                isinstance(kw.value, ast.Constant)
                                and kw.value.value is False
                            ):
                                return True
        except:
            pass
        return False

    def _is_class_var(self, annotation_node):
        try:
            resolved = self.resolve_annotation(annotation_node)
            return "ClassVar" in resolved and (
                resolved.startswith("ClassVar")
                or "typing.ClassVar" in resolved
            )
        except:
            return False

    def _extract_field_default(self, node):
        try:
            if isinstance(node, ast.Call):
                is_field = False
                if isinstance(node.func, ast.Name) and node.func.id in (
                    "Field",
                    "field",
                ):
                    is_field = True
                elif isinstance(
                    node.func, ast.Attribute
                ) and node.func.attr in ("Field", "field"):
                    is_field = True

                if is_field:
                    for kw in node.keywords:
                        if kw.arg == "default":
                            return ast.unparse(kw.value)
                        if kw.arg == "default_factory":
                            val = ast.unparse(kw.value)
                            if val in ("list", "dict", "set"):
                                return f"{val}()"
                            return f"Factory({val})"
                    return None

            return ast.unparse(node)
        except:
            return None

    def _add_prop(
        self,
        name,
        type_hint,
        docstring=None,
        init_excluded=False,
        default_value=None,
    ):
        if self.in_function:
            return

        # Determine target FQN (Class or Module)
        target_fqn = self.current_class_fqn or self.mod_fqn
        
        if target_fqn not in self.structure_map:
            return

        if "props" not in self.structure_map[target_fqn]:
             self.structure_map[target_fqn]["props"] = []

        props = self.structure_map[target_fqn]["props"]
        existing = next((p for p in props if p["name"] == name), None)

        if existing:
            if docstring and not existing.get("docstring"):
                existing["docstring"] = docstring
            if init_excluded:
                existing["init_excluded"] = True
            if default_value is not None:
                existing["default_value"] = default_value
            if existing["type"] == "Any" and type_hint != "Any":
                existing["type"] = type_hint
        else:
            props.append(
                {
                    "name": name,
                    "type": type_hint,
                    "docstring": docstring,
                    "init_excluded": init_excluded,
                    "default_value": default_value,
                }
            )

    def visit_Assign(self, node):
        # Support Class-level and Module-level assignments
        if not self.in_function:
            type_hint = "Any"
            init_excluded = False
            default_value = None

            if node.value:
                default_value = self._extract_field_default(node.value)

            if isinstance(node.value, ast.Constant):
                type_hint = type(node.value.value).__name__
            elif isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name):
                    type_hint = self.imports.get(
                        node.value.func.id, node.value.func.id
                    )
                elif isinstance(node.value.func, ast.Attribute):
                    type_hint = self.resolve_annotation(node.value.func)

                if self._is_init_excluded_field(node.value):
                    init_excluded = True

            for target in node.targets:
                if isinstance(target, ast.Name):
                    # For Class variables, exclude private by default (common practice)
                    # For Module variables, we might want to capture them if they are dependencies
                    # But traditionally private shouldn't be part of Public API.
                    # TC05 requires _private_attr to be captured.
                    # So we relax the check for Module level?
                    
                    is_private = target.id.startswith("_")
                    if self.current_class_fqn and is_private:
                        continue 
                    # If module level, we allow private for now (per plan)
                    
                    self._add_prop(
                        target.id,
                        type_hint,
                        init_excluded=init_excluded,
                        default_value=default_value,
                    )
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if (
            not self.in_function
            and isinstance(node.target, ast.Name)
        ):
            # Same private logic as Assign
            is_private = node.target.id.startswith("_")
            if self.current_class_fqn and is_private:
                # Skip private class members
                pass # logic continues below? No, we should return or skip calling _add_prop
                if is_private: return
            
            # For module level, allow private (TC05)
            
            prop_type = self.resolve_annotation(node.annotation)

            init_excluded = False
            default_value = None

            if self._is_class_var(node.annotation):
                init_excluded = True

            if node.value:
                default_value = self._extract_field_default(node.value)
                if self._is_init_excluded_field(node.value):
                    init_excluded = True

            self._add_prop(
                node.target.id,
                prop_type,
                init_excluded=init_excluded,
                default_value=default_value,
            )
        self.generic_visit(node)

