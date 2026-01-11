import ast
import os
import json
import sys
from pathlib import Path

# Add root to sys.path
sys.path.append(os.getcwd())

from benchmarks.benchmark_generator.tools import UsageVisitor, TargetParameter, TargetType

def get_targets(repo_path):
    root_dir = Path(repo_path).resolve()
    targets = []
    all_files = []
    ignored_dirs = {".git", ".vscode", ".gemini", "__pycache__", "env", "venv", "node_modules", "dist", "build"}
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith(".py") and not file.startswith("test_") and not file.startswith("."):
                all_files.append(Path(root) / file)

    print(f"Scanning {len(all_files)} files for usage...")
    usage_visitor = UsageVisitor()
    for file_path in all_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            usage_visitor.visit(tree)
        except Exception:
            pass
            
    usage_stats = usage_visitor.stats

    print(f"Scanning definitions...")
    for full_path in all_files:
        try:
            relative_path = full_path.relative_to(root_dir)
            module_parts = list(relative_path.parts)
            if module_parts[-1] == "__init__.py":
                module_parts.pop()
            else:
                module_parts[-1] = module_parts[-1][:-3]
            module_name = ".".join(module_parts)

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            class Visitor(ast.NodeVisitor):
                def __init__(self):
                    self.current_class = None
                def visit_ClassDef(self, node):
                    old = self.current_class
                    self.current_class = node.name
                    self.generic_visit(node)
                    self.current_class = old
                def visit_FunctionDef(self, node):
                    if node.name.startswith("_") and not node.name.startswith("__"): return
                    doc = ast.get_docstring(node)
                    comp = node.end_lineno - node.lineno if hasattr(node, "end_lineno") else 0
                    if comp < 3: return
                    
                    if self.current_class:
                        fqn = f"{module_name}.{self.current_class}.{node.name}"
                    else:
                        fqn = f"{module_name}.{node.name}"
                    
                    stats = usage_stats.get(fqn, {})
                    call_count = stats.get("call_count", 0)
                    
                    targets.append({
                        "file_path": str(relative_path),
                        "name": f"{self.current_class}.{node.name}" if self.current_class else node.name,
                        "fqn": fqn,
                        "complexity": comp,
                        "usage": call_count,
                        "docstring": bool(doc)
                    })
            Visitor().visit(tree)
        except Exception: pass
    return targets

targets = get_targets("../adk-python")

def score(t):
    # Same scoring as agents.py/tools.py
    # complexity + usage*20 + doc*10
    s = t["complexity"]
    if t["docstring"]: s += 10
    s += t["usage"] * 20
    return s

targets.sort(key=score, reverse=True)

print(f"\nTop 100 Prioritized Targets (Total Scanned: {len(targets)}):")
print(f"{'Rank':<5} | {'Score':<6} | {'Usage':<5} | {'Target Method':<60} | {'File Path'}")
print("-" * 140)
for i, t in enumerate(targets[:100]):
    print(f"{i+1:<5} | {score(t):<6.1f} | {t['usage']:<5} | {t['fqn'][:60]:<60} | {t['file_path']}")
