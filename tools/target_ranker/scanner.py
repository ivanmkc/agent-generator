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
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict

from google.adk.tools import ToolContext
from benchmarks.generator.benchmark_generator.models import TargetEntity, TargetType

# --- Scanner (Cartographer) Logic ---


def scan_repository(
    repo_path: str,
    tool_context: ToolContext,
    coverage_file: Optional[str] = None,
    namespace: Optional[str] = None,
    root_namespace_prefix: Optional[str] = None,
) -> str:
    """
    Scans the repository to build a hierarchical map of entities.
    Acts as the 'Cartographer' and 'Strategist' by calculating usage-based priority from external statistics.
    Filters entities to stay within the specified namespace if provided.

    Features:
    - Resolves type hints to Fully Qualified Names (FQNs) via import analysis.
    - Handles string forward references and local class definitions.
    """
    root_dir = Path(repo_path).resolve()
    if not root_dir.exists():
        return json.dumps(
            {"error": f"Path {repo_path} (resolved to {root_dir}) does not exist."}
        )

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
        except Exception:
            pass

    # Load Usage Stats (adk_stats.yaml)
    # Allow override via state for testing
    stats_file_override = tool_context.session.state.get("stats_file_path")
    stats_path = (
        Path(stats_file_override)
        if stats_file_override
        else Path("benchmarks/adk_stats.yaml")
    )

    usage_stats = {}
    if stats_path.exists():
        try:
            with open(stats_path, "r") as f:
                usage_stats = yaml.safe_load(f)
        except Exception:
            pass

    # Load Co-occurrence Data (default or override)
    coocc_file_override = tool_context.session.state.get("cooccurrence_file")
    coocc_path = (
        Path(coocc_file_override)
        if coocc_file_override
        else Path("benchmarks/adk_cooccurrence.json")
    )

    cooccurrence_data = {}
    if coocc_path.exists():
        try:
            with open(coocc_path, "r") as f:
                cooccurrence_data = json.load(f)
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
        try:
            relative_path = full_path.relative_to(root_dir)
            module_parts = list(relative_path.parts)
            if module_parts[-1] == "__init__.py":
                module_parts.pop()
            else:
                module_parts[-1] = module_parts[-1][:-3]
            module_fqn = ".".join(module_parts)
            if module_fqn.startswith("src."):
                module_fqn = module_fqn[4:]

            if root_namespace_prefix:
                if module_fqn:
                    module_fqn = f"{root_namespace_prefix}.{module_fqn}"
                else:
                    module_fqn = root_namespace_prefix

            if namespace and not module_fqn.startswith(namespace):
                continue

            # Public API Filter: Skip modules with private components
            if any(part.startswith("_") for part in module_fqn.split(".")):
                continue

            # Blacklist modules known to cause crashes (e.g. segfaults in trace_execution)
            if "spanner" in module_fqn:
                continue

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

            # Module Entity for Ranking
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

            class EntityVisitor(ast.NodeVisitor):

                def __init__(self, mod_fqn, f_path):
                    self.current_class_fqn = None
                    self.in_function = False
                    self.mod_fqn = mod_fqn
                    self.f_path = f_path
                    self.imports = {}
                    self.local_names = set()

                def collect_local_names(self, node):
                    """Pre-scans top-level nodes to identify locally defined classes/functions/types."""
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
                        # level=1 (.) -> current package (mod_fqn)
                        # level=2 (..) -> parent (mod_fqn - 1)
                        if relative_path.name == "__init__.py":
                            cutoff = len(parts) - (node.level - 1)
                        else:
                            cutoff = len(parts) - node.level
                            
                        if cutoff < 0: cutoff = 0
                        prefix = ".".join(parts[:cutoff])
                            
                        if prefix:
                            module = f"{prefix}.{module}" if module else prefix

                    for alias in node.names:
                        name = alias.asname or alias.name
                        if alias.name == "*":
                            continue  # wildcard import - hard to resolve without static analysis
                        self.imports[name] = (
                            f"{module}.{alias.name}" if module else alias.name
                        )

                    # Also populate alias_map for the scanner's structural needs if in __init__
                    if relative_path.name == "__init__.py":
                        canonical_mod = module
                        for alias in node.names:
                            alias_fqn = f"{self.mod_fqn}.{alias.asname or alias.name}"
                            canonical_fqn = f"{canonical_mod}.{alias.name}"
                            
                            # Only add if canonical exists and is NOT a module
                            # AND alias_fqn is NOT itself a module (prevent shadowing issues)
                            if (
                                canonical_fqn in structure_map
                                and structure_map[canonical_fqn]["type"] != "Module"
                                and (alias_fqn not in structure_map or structure_map[alias_fqn]["type"] != "Module")
                            ):
                                alias_map[alias_fqn] = canonical_fqn

                    self.generic_visit(node)

                def resolve_annotation(self, node):
                    """
                    Recursively resolves a type annotation node to its FQN string.

                    Capabilities:
                    - Maps imported names to FQNs using the file's import table.
                    - Resolves local class names to {module_fqn}.{ClassName}.
                    - Parses and resolves string forward references (e.g. 'ToolConfig').
                    - Handles complex types like Optional[List['MyType']].
                    """
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
                            # Recursively resolve the value part (e.g. 'types' in 'types.Content')
                            value_str = self.resolve_annotation(node.value)
                            return f"{value_str}.{node.attr}"

                        elif isinstance(node, ast.Subscript):
                            value_str = self.resolve_annotation(node.value)
                            slice_str = "Any"
                            if hasattr(node, "slice"):  # python < 3.9 used slice
                                slice_node = node.slice
                                if isinstance(
                                    slice_node, ast.Tuple
                                ):  # e.g. Dict[str, int]
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
                            # String forward reference
                            if isinstance(node.value, str):
                                try:
                                    parsed = ast.parse(node.value, mode="eval")
                                    return self.resolve_annotation(parsed.body)
                                except:
                                    return node.value
                            return str(node.value)

                        return ast.unparse(node)
                    except:
                        # Fallback
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
                    structure_map[class_fqn] = {
                        "type": "Class",
                        "name": node.name,
                        "children": [],
                        "params": {},
                        "props": [],
                        "bases": bases,
                        "decorators": decorators,
                    }
                    structure_map[self.mod_fqn]["children"].append(class_fqn)

                    # Entity
                    cls_stats = usage_stats.get(class_fqn, {})
                    entities.append(
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
                                    break  # Just take first target
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

                        # Add self/cls if appropriate (optional for display, but good for completeness)
                        # We skipped 'self' in params dict, but let's see how ast.unparse handles args.
                        # ast.unparse does the whole thing. We need to reconstruct manually to inject resolved types.

                        # Process Positional Args
                        for arg in node.args.args:
                            arg_str = arg.arg
                            if arg.annotation:
                                arg_str += (
                                    f": {self.resolve_annotation(arg.annotation)}"
                                )
                            args_list.append(arg_str)

                        # Process Keyword Only Args
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
                                if default:  # Add default presence indicator or value?
                                    # ast.unparse(default) gives value.
                                    try:
                                        arg_str += f"={ast.unparse(default)}"
                                    except:
                                        arg_str += "=..."
                                args_list.append(arg_str)

                        # Return Type
                        ret_str = ""
                        if node.returns:
                            ret_str = f" -> {self.resolve_annotation(node.returns)}"

                        full_sig = f"def {node.name}({', '.join(args_list)}){ret_str}:"

                        # Structure Map
                        structure_map[func_fqn] = {
                            "type": "Method",
                            "name": node.name,
                            "children": [],
                            "params": params,
                            "props": [],
                            "docstring": doc,
                            "signature": full_sig,
                        }
                        if parent_fqn in structure_map:
                            structure_map[parent_fqn]["children"].append(func_fqn)

                        if node.end_lineno - node.lineno >= 3:
                            # Entity
                            func_stats = usage_stats.get(func_fqn, {})
                            entities.append(
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

                    self.generic_visit(node)
                    self.in_function = old_in_func

                def visit_FunctionDef(self, node):
                    self._visit_any_function(node)

                def visit_AsyncFunctionDef(self, node):
                    self._visit_any_function(node)

                def _is_init_excluded_field(self, node):
                    """Detects if an assignment value is a Field(...) call with init=False."""
                    try:
                        if isinstance(node, ast.Call):
                            # Check for Field/field call (heuristic: name is Field or field)
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
                    """Detects if a type annotation is ClassVar."""
                    try:
                        resolved = self.resolve_annotation(annotation_node)
                        # Check for ClassVar or typing.ClassVar
                        # resolve_annotation returns strings like "ClassVar[...]" or "typing.ClassVar[...]"
                        return "ClassVar" in resolved and (
                            resolved.startswith("ClassVar")
                            or "typing.ClassVar" in resolved
                        )
                    except:
                        return False

                def _extract_field_default(self, node):
                    """Extracts effective default value from Field(...) call or raw value."""
                    try:
                        if isinstance(node, ast.Call):
                            # Check for Field/field call
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
                                return None  # Field used but no static default found

                        # Not a Field call, just use the value
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
                    if not self.current_class_fqn or self.in_function:
                        return

                    props = structure_map[self.current_class_fqn]["props"]
                    existing = next((p for p in props if p["name"] == name), None)

                    if existing:
                        # Merge details
                        if docstring and not existing.get("docstring"):
                            existing["docstring"] = docstring
                        if init_excluded:
                            existing["init_excluded"] = True
                        if default_value is not None:
                            existing["default_value"] = default_value
                        # Update type if we have a better one? (e.g. Any -> specific)
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
                    if self.current_class_fqn and not self.in_function:
                        # Try to infer type from value
                        type_hint = "Any"
                        init_excluded = False
                        default_value = None

                        # Extract default
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

                            # Check for Field(init=False)
                            if self._is_init_excluded_field(node.value):
                                init_excluded = True

                        for target in node.targets:
                            if isinstance(
                                target, ast.Name
                            ) and not target.id.startswith("_"):
                                self._add_prop(
                                    target.id,
                                    type_hint,
                                    init_excluded=init_excluded,
                                    default_value=default_value,
                                )
                    self.generic_visit(node)

                def visit_AnnAssign(self, node):
                    if (
                        self.current_class_fqn
                        and not self.in_function
                        and isinstance(node.target, ast.Name)
                        and not node.target.id.startswith("_")
                    ):
                        prop_type = self.resolve_annotation(node.annotation)

                        init_excluded = False
                        default_value = None

                        # Check ClassVar
                        if self._is_class_var(node.annotation):
                            init_excluded = True

                        if node.value:
                            default_value = self._extract_field_default(node.value)

                            # Check Field(init=False) in value
                            if self._is_init_excluded_field(node.value):
                                init_excluded = True

                        self._add_prop(
                            node.target.id,
                            prop_type,
                            init_excluded=init_excluded,
                            default_value=default_value,
                        )
                    self.generic_visit(node)

                # Removed old visit_ImportFrom that was here, merged into top class logic

            visitor = EntityVisitor(module_fqn, str(relative_path))
            visitor.collect_local_names(tree)
            visitor.visit(tree)
        except Exception:
            pass

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

    # Save scanned data to session state for the Strategist
    tool_context.session.state["scanned_targets"] = [e.model_dump() for e in entities]
    tool_context.session.state["structure_map"] = structure_map
    tool_context.session.state["alias_map"] = alias_map
    tool_context.session.state["usage_stats"] = usage_stats
    tool_context.session.state["cooccurrence_data"] = cooccurrence_data
    tool_context.session.state["coverage_data"] = coverage_data

    # Persist to shared queue file (if output_dir is available) for Worker Pull
    output_dir = tool_context.session.state.get("output_dir")
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        # Save Scanned Targets
        with open(out_path / "scanned_targets.json", "w", encoding="utf-8") as f:
            json.dump([e.model_dump() for e in entities], f)
        # Save Structure Map
        with open(out_path / "structure_map.json", "w", encoding="utf-8") as f:
            json.dump(structure_map, f)

    return f"Cartographer scan complete: {len(entities)} hierarchical entities mapped. Structure map size: {len(structure_map)}."
