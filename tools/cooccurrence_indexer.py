#!/usr/bin/env python3
"""
Co-occurrence Indexer.
Analyzes Python repositories to calculate conditional probabilities of module/class/property usage.
P(B | A) = Count(A and B) / Count(A)
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GranularUsageVisitor(ast.NodeVisitor):
    def __init__(self):
        self.used_entities = set()
        self.imports = {} # alias -> canonical

    def visit_Import(self, node):
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
            self.used_entities.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        if module: self.used_entities.add(module)
        for alias in node.names:
            name = alias.name
            if name == "*": continue
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
        if not name: return name
        parts = name.split('.')
        root = parts[0]
        if root in self.imports:
            resolved_root = self.imports[root]
            return f"{resolved_root}.{'.'.join(parts[1:])}" if len(parts) > 1 else resolved_root
        return name

def analyze_repo(repo_path: Path) -> Tuple[Counter, Dict[str, Counter]]:
    file_counts = Counter()
    co_occurrences = defaultdict(Counter)
    
    python_files = []
    ignored_dirs = {".git", ".vscode", ".gemini", "__pycache__", "env", "venv", "node_modules", "dist", "build"}

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith(".py") and not file.startswith("test_"):
                python_files.append(Path(root) / file)

    logger.info(f"Scanning {len(python_files)} files in {repo_path} for granular usage...")

    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            
            visitor = GranularUsageVisitor()
            visitor.visit(tree)
            
            # Filter for google.adk entities
            relevant = {ent for ent in visitor.used_entities if ent.startswith("google.adk")}
            
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
    temp_dir = Path(tempfile.mkdtemp(prefix="adk_coocc_"))
    logger.info(f"Cloning {url} to {temp_dir}...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, url, str(temp_dir)],
            check=True, capture_output=True
        )
        return temp_dir
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone {url}: {e.stderr.decode()}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Calculate Granular Co-occurrence Probabilities")
    parser.add_argument("--repo", type=str, default="https://github.com/google/adk-samples", help="Repo URL")
    parser.add_argument("--path", type=str, default="python", help="Subpath")
    parser.add_argument("--output", type=str, default="benchmarks/adk_cooccurrence.json", help="Output JSON path")
    
    args = parser.parse_args()
    
    repo_dir = clone_repo(args.repo)
    if not repo_dir: sys.exit(1)
        
    try:
        target_dir = repo_dir / args.path
        counts, co_matrix = analyze_repo(target_dir)
        
        results = []
        for context, count in counts.items():
            if count < 2: continue 
            
            associations = co_matrix[context]
            for target, co_count in associations.items():
                prob = co_count / count
                results.append({
                    "context": context,
                    "target": target,
                    "probability": round(prob, 3),
                    "support": co_count
                })
        
        results.sort(key=lambda x: (x["probability"], x["support"]), reverse=True)
        
        with open(args.output, "w") as f:
            json.dump({
                "meta": {"repo": args.repo, "path": args.path},
                "associations": results
            }, f, indent=2)
            
        logger.info(f"Saved {len(results)} granular associations to {args.output}")
        
    finally:
        shutil.rmtree(repo_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
