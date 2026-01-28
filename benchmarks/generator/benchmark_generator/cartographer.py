"""
The Cartographer Agent: Maps the codebase.

This module defines the logic for the initial discovery phase of the benchmark generation
process. It uses the `TargetRanker` to identify high-value targets (Seed targets)
and their dependencies, creating a prioritized queue for the Generator.
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

"""
Cartographer module for scanning repositories and generating targets.

This module replaces the Agent-based scanning tool with a pure Python
asynchronous generator approach.
"""

import ast
import os
import yaml
import json
import logging
from pathlib import Path
from typing import AsyncIterator, List, Dict, Optional, Set
from collections import deque, defaultdict

from benchmarks.generator.benchmark_generator.models import TargetEntity, TargetType, ContextNode

logger = logging.getLogger(__name__)


class Cartographer:
    """
    Scans a repository to identify valid benchmarking targets (Classes/Methods).
    Enriches targets with usage statistics and co-occurrence context.
    """

    def __init__(
        self,
        repo_path: str,
        stats_file: Optional[str] = None,
        cooccurrence_file: Optional[str] = None,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.usage_stats = self._load_stats(stats_file)
        self.cooccurrence_data = self._load_cooccurrence(cooccurrence_file)
        self.structure_map = {}  # FQN -> AST/Metadata
        self.alias_map = {}  # Alias FQN -> Canonical FQN

    def _load_stats(self, path: Optional[str]) -> Dict:
        if not path:
            path = "benchmarks/adk_stats.yaml"
        try:
            if Path(path).exists():
                with open(path, "r") as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load usage stats from {path}: {e}")
        return {}

    def _load_cooccurrence(self, path: Optional[str]) -> Dict:
        if not path:
            path = "benchmarks/adk_cooccurrence.json"
        try:
            if Path(path).exists():
                with open(path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cooccurrence data from {path}: {e}")
        return {}

    async def scan(
        self, namespace: Optional[str] = None
    ) -> AsyncIterator[TargetEntity]:
        """
        Async generator that yields enriched TargetEntities from the repository.
        """
        if not self.repo_path.exists():
            logger.error(f"Repository path {self.repo_path} does not exist.")
            return

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
        all_python_files = []

        # 1. Walk and collect files
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                if (
                    file.endswith(".py")
                    and not file.startswith("test_")
                    and not file.startswith(".")
                ):
                    all_python_files.append(Path(root) / file)

        # 2. First Pass: Build Structure Map (needed for context resolution)
        # We need to process all files to build the structure map *before* yielding fully context-aware entities?
        # Or we can build it incrementally. For full context resolution, we ideally need the map.
        # But to keep it streaming, we might have to accept partial context or do a fast first pass.
        # Let's do a fast synchronous parse first to build the map, then yield.

        logger.info(f"Scanning {len(all_python_files)} files to build structure map...")
        for file_path in all_python_files:
            self._parse_file_structure(file_path, namespace)

        logger.info(
            f"Structure map built with {len(self.structure_map)} entries. Streaming targets..."
        )

        # 3. Second Pass: Yield Entities
        # We iterate through the structure map (or the files again) and yield targets.
        # Since we already have the nodes in structure_map, we can iterate that.
        # However, structure_map doesn't store the full AST node for memory reasons usually.
        # Let's re-parse or store enough metadata.

        # Actually, let's just iterate the structure_map keys that are valid targets.
        # But we need the source code! The original tool `select_target` reads the file.
        # So we should yield basic info, and let the downstream `map` step load source code if selected.
        # Wait, the prompt said "Observer receives a specific TargetEntity (with source code injected)".
        # So we should inject it here or in a map step.

        # To support true streaming without holding everything in memory,
        # we can iterate the files again and yield entities as we parse them.
        # We use the pre-built structure_map only for *context resolution* (finding neighbors).

        for file_path in all_python_files:
            relative_path = file_path.relative_to(self.repo_path)
            module_fqn = self._get_module_fqn(relative_path)

            if namespace and not module_fqn.startswith(namespace):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content)

                # Visit and yield
                visitor = self._EntityYieldingVisitor(
                    self, module_fqn, str(relative_path), content
                )
                visitor.visit(tree)

                for entity in visitor.entities:
                    # Enrich with context before yielding
                    self._enrich_context(entity)
                    yield entity

            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")

    def _get_module_fqn(self, relative_path: Path) -> str:
        parts = list(relative_path.parts)
        if parts[-1] == "__init__.py":
            parts.pop()
        else:
            parts[-1] = parts[-1][:-3]
        fqn = ".".join(parts)
        if fqn.startswith("src."):
            fqn = fqn[4:]
        return fqn

    def _parse_file_structure(self, file_path: Path, namespace: Optional[str]):
        try:
            relative_path = file_path.relative_to(self.repo_path)
            module_fqn = self._get_module_fqn(relative_path)

            if namespace and not module_fqn.startswith(namespace):
                return

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)

            # Register Module
            self.structure_map[module_fqn] = {
                "type": "Module",
                "children": [],
                "file_path": str(relative_path),
            }

            class StructureVisitor(ast.NodeVisitor):

                def __init__(self, cartographer, mod_fqn):
                    self.cart = cartographer
                    self.mod_fqn = mod_fqn
                    self.current_class = None

                def visit_ClassDef(self, node):
                    if node.name.startswith("_"):
                        return
                    class_fqn = f"{self.mod_fqn}.{node.name}"
                    self.cart.structure_map[class_fqn] = {
                        "type": "Class",
                        "children": [],
                        "parent": self.mod_fqn,
                    }
                    self.cart.structure_map[self.mod_fqn]["children"].append(class_fqn)

                    old_class = self.current_class
                    self.current_class = class_fqn
                    self.generic_visit(node)
                    self.current_class = old_class

                def visit_FunctionDef(self, node):
                    if node.name.startswith("_") and node.name != "__init__":
                        return
                    parent = self.current_class or self.mod_fqn
                    func_fqn = f"{parent}.{node.name}"
                    self.cart.structure_map[func_fqn] = {
                        "type": "Method",
                        "children": [],
                        "parent": parent,
                    }
                    if parent in self.cart.structure_map:
                        self.cart.structure_map[parent]["children"].append(func_fqn)

                def visit_ImportFrom(self, node):
                    # Basic alias mapping logic if needed
                    pass

            StructureVisitor(self, module_fqn).visit(tree)
        except Exception:
            pass

    def _enrich_context(self, entity: TargetEntity):
        """Populates associated_context using BFS on the co-occurrence graph."""
        associations = self.cooccurrence_data.get("associations", [])
        if not associations:
            return

        # Simple BFS logic reuse
        prob_map = defaultdict(dict)
        for a in associations:
            prob_map[a["context"]][a["target"]] = a["probability"]

        # Find start node in graph
        parts = entity.id.split(".")
        start_node = None
        for i in range(len(parts), 0, -1):
            sub = ".".join(parts[:i])
            if sub in prob_map:
                start_node = sub
                break

        if not start_node:
            return

        queue = deque([(start_node, 1.0)])
        final_probs = {start_node: 1.0}

        while queue and len(final_probs) < 8:
            curr, p = queue.popleft()
            neighbors = sorted(
                prob_map.get(curr, {}).items(), key=lambda x: x[1], reverse=True
            )
            for neighbor, cond_p in neighbors:
                new_p = p * cond_p
                if new_p >= 0.05 and new_p > final_probs.get(neighbor, 0.0):
                    final_probs[neighbor] = new_p
                    queue.append((neighbor, new_p))

        context_nodes = []
        for node_fqn, prob in sorted(
            final_probs.items(), key=lambda x: x[1], reverse=True
        ):
            info = self.structure_map.get(node_fqn, {})
            context_nodes.append(
                ContextNode(
                    id=node_fqn,
                    type=info.get("type", "Unknown"),
                    probability=prob,
                    usage=self.usage_stats.get(node_fqn, {}).get("total_calls", 0),
                    parent_id=info.get("parent"),
                )
            )

        entity.associated_context = context_nodes

    class _EntityYieldingVisitor(ast.NodeVisitor):
        """Visits AST and creates TargetEntity objects."""

        def __init__(self, cartographer, mod_fqn, file_path, source_content):
            self.cart = cartographer
            self.mod_fqn = mod_fqn
            self.file_path = file_path
            self.source_content = source_content
            self.entities = []
            self.current_class = None

        def visit_ClassDef(self, node):
            if node.name.startswith("_"):
                return
            class_fqn = f"{self.mod_fqn}.{node.name}"

            # Extract source code for class
            source_segment = ast.get_source_segment(self.source_content, node)

            entity = TargetEntity(
                id=class_fqn,
                type=TargetType.CLASS,
                name=node.name,
                file_path=self.file_path,
                usage_score=self.cart.usage_stats.get(class_fqn, {}).get(
                    "total_calls", 0
                ),
                docstring=ast.get_docstring(node),
                source_code=source_segment,
                parent_id=self.mod_fqn,
            )
            self.entities.append(entity)

            old_class = self.current_class
            self.current_class = class_fqn
            self.generic_visit(node)
            self.current_class = old_class

        def visit_FunctionDef(self, node):
            if node.name.startswith("_") and node.name != "__init__":
                return
            parent = self.current_class or self.mod_fqn
            func_fqn = f"{parent}.{node.name}"

            complexity = (
                node.end_lineno - node.lineno if hasattr(node, "end_lineno") else 0
            )
            if complexity < 3:
                return

            source_segment = ast.get_source_segment(self.source_content, node)

            entity = TargetEntity(
                id=func_fqn,
                type=TargetType.METHOD,
                name=node.name,
                file_path=self.file_path,
                usage_score=self.cart.usage_stats.get(func_fqn, {}).get(
                    "total_calls", 0
                ),
                complexity_score=float(complexity),
                docstring=ast.get_docstring(node),
                source_code=source_segment,
                parent_id=parent,
            )
            self.entities.append(entity)
