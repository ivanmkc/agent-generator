#!/usr/bin/env python3
"""
AST-based API Usage Indexer.
Scans Python repositories to count function/class usage frequencies.
Outputs a YAML index for the Statistical Discovery Tool.
"""

import ast
import os
import sys
import shutil
import subprocess
import tempfile
import argparse
import logging
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

# Try to import yaml, fallback to json if not available (though spec says yaml)
try:
    import yaml
except ImportError:
    print("PyYAML not found. Please install it: pip install PyYAML")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UsageVisitor(ast.NodeVisitor):
    def __init__(self):
        # Maps FQN (guessed) -> usage stats
        self.stats = defaultdict(lambda: {
            "call_count": 0,
            "arg_usage": Counter()
        })
        # Track imports to resolve aliases: alias -> real_name
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
            if name == "*":
                continue # Wildcard imports hard to track statically
            full_name = f"{module}.{name}" if module else name
            self.imports[asname] = full_name
        self.generic_visit(node)

    def visit_Call(self, node):
        func_name = self._get_func_name(node.func)
        if func_name:
            # Resolve alias
            resolved_name = self._resolve_name(func_name)
            
            self.stats[resolved_name]["call_count"] += 1
            
            # Count keyword args
            for keyword in node.keywords:
                if keyword.arg:
                    self.stats[resolved_name]["arg_usage"][keyword.arg] += 1
                    
        self.generic_visit(node)

    def _get_func_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_func_name(node.value) + "." + node.attr
        return None

    def _resolve_name(self, name):
        parts = name.split('.')
        # Try to resolve the root
        root = parts[0]
        if root in self.imports:
            resolved_root = self.imports[root]
            return resolved_root + "." + ".".join(parts[1:]) if len(parts) > 1 else resolved_root
        return name

def analyze_directory(path: Path) -> Dict[str, Any]:
    visitor = UsageVisitor()
    
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=str(file_path))
                    visitor.visit(tree)
                except Exception as e:
                    logger.warning(f"Failed to parse {file_path}: {e}")
    
    return visitor.stats

def merge_stats(global_stats, new_stats):
    for func, data in new_stats.items():
        if func not in global_stats:
            global_stats[func] = {
                "call_count": 0,
                "arg_usage": Counter()
            }
        global_stats[func]["call_count"] += data["call_count"]
        global_stats[func]["arg_usage"].update(data["arg_usage"])

def clone_repo(url: str, branch: str = "main") -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="adk_indexer_"))
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
    parser = argparse.ArgumentParser(description="Generate Statistical API Index")
    parser.add_argument("--config", type=str, help="Path to YAML config file (sources)")
    parser.add_argument("--output", type=str, default="api_metadata.yaml", help="Output YAML path")
    # Quick mode: direct repo url
    parser.add_argument("--repo", type=str, help="Direct repo URL to analyze")
    parser.add_argument("--path", type=str, help="Subpath within repo (e.g. python/examples)")
    
    args = parser.parse_args()
    
    global_stats = {}
    
    sources = []
    if args.config:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
            sources = config.get('sources', [])
    elif args.repo:
        sources = [{"url": args.repo, "include_paths": [args.path] if args.path else None}]
        
    if not sources:
        print("No sources provided. Use --config or --repo")
        sys.exit(1)
        
    temp_dirs = []
    
    try:
        for source in sources:
            url = source.get("url")
            branch = source.get("branch", "main")
            repo_dir = clone_repo(url, branch)
            if repo_dir:
                temp_dirs.append(repo_dir)
                
                include_paths = source.get("include_paths")
                if include_paths:
                    for p in include_paths:
                        target = repo_dir / p
                        if target.exists():
                            logger.info(f"Analyzing {target}...")
                            stats = analyze_directory(target)
                            merge_stats(global_stats, stats)
                        else:
                            logger.warning(f"Path {target} not found in repo.")
                else:
                    logger.info(f"Analyzing {repo_dir}...")
                    stats = analyze_directory(repo_dir)
                    merge_stats(global_stats, stats)
    finally:
        for d in temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    # Post-process: Convert Counters to dicts and calculate frequencies
    final_index = {}
    
    # Filter for google.adk packages only (reduce noise)
    target_prefixes = ["google.adk", "adk"]
    
    for func, data in global_stats.items():
        # Heuristic filter
        if not any(p in func for p in target_prefixes):
            continue
            
        total = data["call_count"]
        if total < 2: continue # Noise filter
        
        args_data = {}
        for arg, count in data["arg_usage"].items():
            freq = count / total
            args_data[arg] = {
                "freq": round(freq, 2),
                "count": count
            }
            
        final_index[func] = {
            "total_calls": total,
            "args": args_data
        }

    logger.info(f"Writing index with {len(final_index)} entries to {args.output}")
    with open(args.output, "w") as f:
        yaml.dump(final_index, f, sort_keys=True)

if __name__ == "__main__":
    main()
