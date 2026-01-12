#!/usr/bin/env python3
"""
ADK Probabilistic Chain Analyzer.

This utility visualizes the 'API Surface' of the ADK framework as a probabilistic dependency tree.
Starting from a root node (e.g., google.adk.agents.Agent), it uses a BFS-based Chain Rule
algorithm to determine what other modules, classes, and methods are statistically likely
to be relevant based on real-world usage in adk-samples.

Main logic:
1. Load physical structure (Module -> Class -> Method -> Parameter).
2. Load co-occurrence data (P(B|A)).
3. Calculate transitive probabilities: P(N) = P(Parent) * P(N|Parent).
4. Render a hierarchical ASCII tree sorted by probability.
"""

import json
import sys
import argparse
import ast
import os
import yaml
from pathlib import Path
from collections import defaultdict, deque

def get_physical_structure(repo_path):
    """
    Scans a repository to build a static hierarchy map and alias resolution map.
    
    Args:
        repo_path: Path to the ADK python source code.
        
    Returns:
        tuple: (node_map, alias_map)
            - node_map: Dict mapping FQN to definition metadata (Type, Children, Params, Props).
            - alias_map: Dict mapping public aliases to canonical FQNs.
    """
    root_dir = Path(repo_path).resolve()
    node_map = {}
    alias_map = {}
    python_files = []
    ignored_dirs = {'.git', '.vscode', '.gemini', '__pycache__', 'env', 'venv', 'node_modules', 'dist', 'build'}
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith(".py") and not file.startswith("test_") and not file.startswith("."):
                python_files.append(Path(root) / file)

    for full_path in python_files:
        try:
            relative_path = full_path.relative_to(root_dir)
            module_parts = list(relative_path.parts)
            if module_parts[-1] == "__init__.py": module_parts.pop()
            else: module_parts[-1] = module_parts[-1][:-3]
            module_fqn = ".".join(module_parts)
            if module_fqn.startswith("src."): module_fqn = module_fqn[4:]
            
            if module_fqn not in node_map:
                node_map[module_fqn] = {"type": "Module", "name": module_parts[-1] if module_parts else "root", "children": [], "params": {}, "props": []}

            with open(full_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            class StructVisitor(ast.NodeVisitor):
                def __init__(self, mod_fqn):
                    self.current_class_fqn = None
                    self.mod_fqn = mod_fqn
                def visit_ClassDef(self, node):
                    if node.name.startswith("_"): return
                    class_fqn = f"{self.mod_fqn}.{node.name}"
                    node_map[class_fqn] = {"type": "Class", "name": node.name, "children": [], "params": {}, "props": []}
                    node_map[self.mod_fqn]["children"].append(class_fqn)
                    old = self.current_class_fqn
                    self.current_class_fqn = class_fqn
                    self.generic_visit(node)
                    self.current_class_fqn = old
                def visit_FunctionDef(self, node):
                    if node.name.startswith("_") and node.name != "__init__": return
                    parent_fqn = self.current_class_fqn or self.mod_fqn
                    func_fqn = f"{parent_fqn}.{node.name}"
                    params = {arg.arg: (ast.unparse(arg.annotation) if arg.annotation else "Any") for arg in node.args.args if arg.arg != "self"}
                    node_map[func_fqn] = {"type": "Method", "name": node.name, "children": [], "params": params, "props": []}
                    if parent_fqn in node_map:
                        node_map[parent_fqn]["children"].append(func_fqn)
                def visit_Assign(self, node):
                    if self.current_class_fqn:
                        for target in node.targets:
                            if isinstance(target, ast.Name) and not target.id.startswith("_"):
                                node_map[self.current_class_fqn]["props"].append(target.id)
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
            StructVisitor(module_fqn).visit(tree)
        except Exception: pass
    return node_map, alias_map

def main():
    parser = argparse.ArgumentParser(description="Visualize ADK dependencies as a probabilistic tree.")
    parser.add_argument("--start", type=str, default="google.adk.agents.Agent", help="Starting identifier (FQN)")
    parser.add_argument("--threshold", type=float, default=0.01, help="Probability threshold for pruning")
    parser.add_argument("--data", type=str, default="benchmarks/adk_cooccurrence.json", help="Path to co-occurrence data")
    parser.add_argument("--repo", type=str, default="../adk-python", help="Path to ADK repository")
    parser.add_argument("--top", type=int, default=40, help="Max nodes to display in root list")
    args = parser.parse_args()
    
    if not Path(args.data).exists():
        print(f"Data file not found: {args.data}")
        sys.exit(1)
        
    structure, alias_map = get_physical_structure(args.repo)
    usage_stats = {}
    if Path("benchmarks/adk_stats.yaml").exists():
        with open("benchmarks/adk_stats.yaml", "r") as f:
            usage_stats = yaml.safe_load(f)

    def resolve_fqn(name):
        if name in structure: return name
        if name in alias_map: return resolve_fqn(alias_map[name])
        name_parts = name.split(".")
        last = name_parts[-1]
        candidates = [k for k in structure.keys() if k.endswith(f".{last}") or k == last]
        if candidates:
            return max(candidates, key=lambda x: len(os.commonprefix([x, name])))
        return name

    with open(args.data, "r") as f:
        coocc_data = json.load(f).get("associations", [])
    
    prob_map = defaultdict(dict)
    for a in coocc_data:
        prob_map[a["context"]][a["target"]] = a["probability"]

    queue = deque([(args.start, 1.0)])
    final_probs = {args.start: 1.0}
    
    print(f"Generating Dependency Tree from: {args.start}\n")
    
    while queue:
        curr, p = queue.popleft()
        for neighbor, cond_p in prob_map.get(curr, {}).items():
            new_p = p * cond_p
            if new_p >= args.threshold and new_p > final_probs.get(neighbor, 0.0):
                final_probs[neighbor] = new_p
                queue.append((neighbor, new_p))

    sorted_results = sorted(final_probs.items(), key=lambda x: x[1], reverse=True)
    
    print(f"{ 'Rank':<5} | {'Chain P':<8} | {'Type':<8} | {'Identifier'}")
    print("-" * 120)

    unwrapped_types = set()

    def print_node_recursive(node_fqn, prob=None, indent=0, label=""):
        canonical = resolve_fqn(node_fqn)
        node_def = structure.get(canonical)
        node_type = node_def["type"] if node_def else "Unknown"
        display_name = node_fqn
        prefix = "  " * indent
        prob_str = f"{prob:.4f}" if prob is not None else ""
        
        if indent == 0:
            print(f"{i:<5} | {prob_str:<8} | {node_type:<8} | {display_name:<60} {label}")
        else:
            icon = "©️" if node_type == "Class" else "ƒ" if node_type == "Method" else "📦"
            if "Type" in label: icon = "↳"
            p_val = f"[P:{prob:.2f}]" if prob is not None else ""
            print(f"{ '':<5} | { '':<8} | { '':<8} | {prefix}{icon} {node_def['name'] if node_def else display_name:<40} {p_val} {label}")

        if not node_def: return

        if node_type == "Class":
            for prop in node_def["props"]:
                p_fqn = f"{canonical}.{prop}"
                p_prob = prob_map.get(node_fqn, {}).get(p_fqn, 0.0)
                if p_prob > 0:
                     print(f"{ '':<5} | { '':<8} | { '':<8} | {prefix}  🔸 {prop:<36} [P:{p_prob:.2f}]")
            
            for child_fqn in node_def["children"]:
                child_def = structure.get(child_fqn)
                if child_def and child_def["type"] == "Method":
                    m_usage = usage_stats.get(child_fqn, {}).get("total_calls", 0)
                    parent_usage = usage_stats.get(canonical, {}).get("total_calls", 0)
                    if child_def["name"] == "__init__" and parent_usage > 0: m_usage = parent_usage
                    m_prob = 0.0
                    if parent_usage > 0: m_prob = m_usage / parent_usage
                    elif m_usage > 0: m_prob = 1.0
                    if m_prob > 0:
                        print_node_recursive(child_fqn, m_prob, indent + 1)

        if node_type == "Method":
             p_stats = usage_stats.get(canonical, {}).get("args", {})
             method_usage = usage_stats.get(canonical, {}).get("total_calls", 0)
             is_init = node_def["name"] == "__init__"
             sorted_params = sorted(node_def["params"].items(), key=lambda x: p_stats.get(x[0], {}).get("count", 0), reverse=True)
             for p_name, p_type in sorted_params:
                 p_count = p_stats.get(p_name, {}).get("count", 0)
                 p_prob = p_count / method_usage if method_usage > 0 else (1.0 if is_init else 0.0)
                 if p_prob > 0:
                     print(f"{ '':<5} | { '':<8} | { '':<8} | {prefix}  🔹 {p_name:<20} ({p_type}) [P:{p_prob:.2f}]")
                     if indent < 6: 
                         for word in p_type.replace("[", " ").replace("]", " ").replace("|", " ").split():
                             type_fqn = resolve_fqn(word)
                             if type_fqn in structure and type_fqn != canonical and type_fqn not in unwrapped_types:
                                 unwrapped_types.add(type_fqn)
                                 print_node_recursive(type_fqn, None, indent + 2, label="(Type Dependency)")
                                 unwrapped_types.remove(type_fqn)

    for i, (node_name, prob) in enumerate(sorted_results):
        if node_name == args.start: continue
        if i > args.top: break
        canonical = resolve_fqn(node_name)
        node_def = structure.get(canonical)
        if node_def and node_def["type"] in ["Module", "Class"]:
             print_node_recursive(node_name, prob, indent=0)

if __name__ == "__main__":
    main()
