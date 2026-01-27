#!/usr/bin/env python3
"""
ADK Co-occurrence Indexer.

This utility scans a Python repository (e.g., adk-samples) to calculate the 
conditional probabilities of ADK module and class usage. It determines the 
likelihood that one component is used given the presence of another in the same file.

P(B | A) = Count(A and B) / Count(A)

The output is a JSON file containing these associations, which is used by the 
Agentic Auditor and the Chain Prob Analyzer to build realistic, integrated 
benchmarking scenarios.

Key tracking:
- Module imports (from x import y)
- Class instantiations (Class())
- Attribute access (Class.property)
"""

import ast
import os
import sys
import argparse
import json
import logging
import shutil
import subprocess
import tempfile
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, Set, List, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GranularUsageVisitor(ast.NodeVisitor):
    """AST Visitor that tracks granular usage of ADK entities within a file."""

    def __init__(self):
        self.used_entities = set()
        self.imports = {}  # alias -> canonical

    def visit_Import(self, node):
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
            self.used_entities.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        if module:
            self.used_entities.add(module)
        for alias in node.names:
            name = alias.name
            if name == "*":
                continue
            full_name = f"{module}.{name}" if module else name
            self.imports[alias.asname or alias.name] = full_name
            self.used_entities.add(full_name)
        self.generic_visit(node)

    def visit_Call(self, node):
        name = self._get_full_name(node.func)
        if name:
            resolved = self._resolve_name(name)
            self.used_entities.add(resolved)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        name = self._get_full_name(node)
        if name:
            resolved = self._resolve_name(name)
            self.used_entities.add(resolved)
        self.generic_visit(node)

    def _get_full_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_full_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        return None

    def _resolve_name(self, name):
        if not name:
            return name
        parts = name.split(".")
        root = parts[0]
        if root in self.imports:
            resolved_root = self.imports[root]
            return (
                f"{resolved_root}.{'.'.join(parts[1:])}"
                if len(parts) > 1
                else resolved_root
            )
        return name


def analyze_repo(repo_path: Path) -> Tuple[Counter, Dict[str, Counter]]:
    """Scans the repo and builds the co-occurrence counts."""
    file_counts = Counter()
    co_occurrences = defaultdict(Counter)

    python_files = []
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

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith(".py") and not file.startswith("test_"):
                python_files.append(Path(root) / file)

    logger.info(
        f"Scanning {len(python_files)} files in {repo_path} for granular usage..."
    )

    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            visitor = GranularUsageVisitor()
            visitor.visit(tree)

            # Filter for google.adk entities
            relevant = {
                ent for ent in visitor.used_entities if ent.startswith("google.adk")
            }
            if not relevant:
                continue

            for ent in relevant:
                file_counts[ent] += 1
                for other in relevant:
                    if ent != other:
                        co_occurrences[ent][other] += 1
        except Exception:
            pass

    return file_counts, co_occurrences


def clone_repo(url: str, branch: str = "main") -> Path:
    """Clones a repo to a temporary directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix="adk_coocc_"))
    logger.info(f"Cloning {url} to {temp_dir}...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, url, str(temp_dir)],
            check=True,
            capture_output=True,
        )
        return temp_dir
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone {url}: {e.stderr.decode()}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Calculate ADK Co-occurrence Probabilities."
    )
    parser.add_argument(
        "--repo",
        type=str,
        help="Repo URL to analyze (optional if --repo-paths is used)",
    )
    parser.add_argument(
        "--repo-paths",
        type=str,
        nargs="+",
        help="List of local repository paths to scan",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="",
        help="Subpath within the repo (only used with --repo)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmarks/adk_cooccurrence.json",
        help="Output path for JSON stats",
    )

    args = parser.parse_args()

    temp_dirs = []
    scan_targets = []

    try:
        if args.repo_paths:
            for p in args.repo_paths:
                resolved = Path(p).resolve()
                if resolved.exists():
                    scan_targets.append(resolved)
                else:
                    logger.warning(f"Path not found: {p}")

        elif args.repo:
            repo_dir = clone_repo(args.repo)
            if repo_dir:
                temp_dirs.append(repo_dir)
                scan_targets.append(repo_dir / args.path)
            else:
                sys.exit(1)
        else:
            parser.error("Must provide either --repo-paths or --repo")

        total_counts = Counter()
        total_co_occurrences = defaultdict(Counter)

        for target in scan_targets:
            c, co = analyze_repo(target)
            total_counts.update(c)
            for key, val in co.items():
                total_co_occurrences[key].update(val)

        results = []
        for context, count in total_counts.items():
            if count < 2:
                continue  # Noise filter

            associations = total_co_occurrences[context]
            for target, co_count in associations.items():
                prob = co_count / count
                results.append(
                    {
                        "context": context,
                        "target": target,
                        "probability": round(prob, 3),
                        "support": co_count,
                    }
                )

        results.sort(key=lambda x: (x["probability"], x["support"]), reverse=True)

        # Ensure output directory exists
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)

        with open(args.output, "w") as f:
            json.dump(
                {
                    "meta": {"repo_paths": [str(p) for p in scan_targets]},
                    "associations": results,
                },
                f,
                indent=2,
            )

        logger.info(f"Saved {len(results)} granular associations to {args.output}")

    finally:
        for t in temp_dirs:
            shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    main()
