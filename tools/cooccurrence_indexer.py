#!/usr/bin/env python3
"""
Co-occurrence Indexer.
Analyzes Python repositories to calculate conditional probabilities of module usage.
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

class ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        # We track the module being imported from
        if module:
            self.imports.add(module)
        # Optionally track specific members if needed, but module-level is usually better for 'context'
        # for alias in node.names:
        #     if module:
        #         self.imports.add(f"{module}.{alias.name}")
        #     else:
        #         self.imports.add(alias.name)
        self.generic_visit(node)

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

    logger.info(f"Scanning {len(python_files)} files in {repo_path}...")

    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            
            visitor = ImportVisitor()
            visitor.visit(tree)
            
            # Filter for google.adk modules to keep it relevant
            relevant_imports = {imp for imp in visitor.imports if imp.startswith("google.adk")}
            
            if not relevant_imports:
                continue

            # Update counts
            for imp in relevant_imports:
                file_counts[imp] += 1
                for other in relevant_imports:
                    if imp != other:
                        co_occurrences[imp][other] += 1
                        
        except Exception:
            pass # Ignore parse errors

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
    parser = argparse.ArgumentParser(description="Calculate Module Co-occurrence Probabilities")
    parser.add_argument("--repo", type=str, default="https://github.com/google/adk-samples", help="Repo URL")
    parser.add_argument("--path", type=str, default="python", help="Subpath")
    parser.add_argument("--output", type=str, default="benchmarks/adk_cooccurrence.json", help="Output JSON path")
    parser.add_argument("--top", type=int, default=20, help="Show top N associations")
    
    args = parser.parse_args()
    
    repo_dir = clone_repo(args.repo)
    if not repo_dir:
        sys.exit(1)
        
    try:
        target_dir = repo_dir / args.path
        counts, co_matrix = analyze_repo(target_dir)
        
        # Calculate Probabilities
        results = []
        for context_module, count in counts.items():
            if count < 2: continue # Ignore rare modules
            
            associations = co_matrix[context_module]
            for target_module, co_count in associations.items():
                prob = co_count / count
                results.append({
                    "context": context_module,
                    "target": target_module,
                    "probability": round(prob, 3),
                    "support": co_count,
                    "confidence": round(prob * 100, 1)
                })
        
        # Sort by Probability desc, then Support desc
        results.sort(key=lambda x: (x["probability"], x["support"]), reverse=True)
        
        print(f"\nTop {args.top} Strongest Module Associations (P(Target | Context)):")
        print(f"{ 'Context (If you use...)':<50} | { 'Target (You likely also use...)':<50} | {'Prob':<6} | {'Count'}")
        print("-" * 120)
        
        for r in results[:args.top]:
            print(f"{r['context']:<50} | {r['target']:<50} | {r['probability']:<6.2f} | {r['support']}")
            
        # Save to JSON
        with open(args.output, "w") as f:
            json.dump({
                "meta": {"repo": args.repo, "path": args.path},
                "associations": results
            }, f, indent=2)
            
        logger.info(f"Saved {len(results)} associations to {args.output}")
        
    finally:
        shutil.rmtree(repo_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
