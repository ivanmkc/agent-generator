import ast
import os
import json
import sys
import yaml
from pathlib import Path
from collections import Counter, defaultdict

# Add root to sys.path
sys.path.append(os.getcwd())

from benchmarks.benchmark_generator.models import TargetEntity, TargetType

def get_targets(repo_path, stats_path):
    root_dir = Path(repo_path).resolve()
    entities = []
    all_python_files = []
    ignored_dirs = {'.git', '.vscode', '.gemini', '__pycache__', 'env', 'venv', 'node_modules', 'dist', 'build'}
    
    # Load stats
    usage_stats = {}
    if Path(stats_path).exists():
        with open(stats_path, "r") as f:
            usage_stats = yaml.safe_load(f)
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith(".py") and not file.startswith("test_") and not file.startswith("."):
                all_python_files.append(Path(root) / file)

    for full_path in all_python_files:
        try:
            relative_path = full_path.relative_to(root_dir)
            module_parts = list(relative_path.parts)
            if module_parts[-1] == "__init__.py": module_parts.pop()
            else: module_parts[-1] = module_parts[-1][:-3]
            module_fqn = ".".join(module_parts)

            lookup_fqn = module_fqn
            if lookup_fqn.startswith("src."):
                lookup_fqn = lookup_fqn[4:]
            
            if not lookup_fqn.startswith("google.adk"):
                continue

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)

            mod_stats = usage_stats.get(lookup_fqn, {})
            
            entities.append(TargetEntity(
                id=lookup_fqn,
                type=TargetType.MODULE,
                name=module_parts[-1],
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
                    parent_id = self.current_class_fqn or self.mod_fqn
                    func_fqn = f"{parent_id}.{node.name}"
                    func_stats = usage_stats.get(func_fqn, {})
                    entities.append(TargetEntity(
                        id=func_fqn,
                        type=TargetType.METHOD,
                        name=node.name,
                        file_path=self.f_path,
                        usage_score=func_stats.get("total_calls", 0),
                        docstring=ast.get_docstring(node),
                        parent_id=parent_id
                    ))

            EntityVisitor(lookup_fqn, str(relative_path)).visit(tree)
        except Exception: pass
    
    return entities

targets = get_targets("../adk-python", "benchmarks/adk_stats.yaml")

# --- Tree Building & Aggregation ---

tree = defaultdict(list)
node_map = {t.id: t for t in targets}
effective_scores = defaultdict(float)

# Base scores
for t in targets:
    s = t.usage_score * 100
    if t.docstring: s += 10
    effective_scores[t.id] = s

# Build Tree Structure
roots = []
for t in targets:
    if t.parent_id and t.parent_id in node_map:
        tree[t.parent_id].append(t)
    else:
        # If parent_id is missing OR parent is not in our filtered set (e.g. parent is outside google.adk?)
        # But here logic ensures parent is constructed from module_fqn which starts with google.adk.
        # However, modules like 'google.adk.tools' might be parents of 'google.adk.tools.agent_tool'.
        # My current logic flatly lists modules as roots.
        # I should try to reconstruct module hierarchy too.
        # For now, treat modules as roots.
        roots.append(t)

# Aggregate Scores (Bubble Up)
# Simple approach: Post-order traversal?
# Or just propagate up for N levels.
# Since we have parent_id for Classes/Methods, we can bubble up to Module.
# Modules don't have parent_id set in my logic (it's None).
# I should link modules to their parent modules?
# e.g. google.adk.tools.agent_tool -> parent: google.adk.tools
# Let's add that logic.

# Improve Module Linking
modules = [t for t in targets if t.type == TargetType.MODULE]
module_map = {m.id: m for m in modules}

for m in modules:
    parts = m.id.split('.')
    if len(parts) > 1:
        parent_fqn = ".".join(parts[:-1])
        if parent_fqn in module_map:
            m.parent_id = parent_fqn
            tree[parent_fqn].append(m)
            # Remove from roots if it was there
            if m in roots:
                roots.remove(m)

# Recalculate Roots
roots = [t for t in targets if not t.parent_id or t.parent_id not in node_map]

def aggregate_score(node):
    s = effective_scores[node.id]
    children = tree[node.id]
    for child in children:
        s += aggregate_score(child)
    effective_scores[node.id] = s # Update with cumulative
    return s

for root in roots:
    aggregate_score(root)

roots.sort(key=lambda x: effective_scores[x.id], reverse=True)

def print_node(node, indent=0):
    s = effective_scores[node.id]
    u = node.usage_score
    icon = "📦" if node.type == TargetType.MODULE else "©️" if node.type == TargetType.CLASS else "ƒ"
    prefix = "  " * indent
    
    # Only print if this branch has value
    if s < 10: return

    print(f"{prefix}{icon} {node.name:<30} | Usage: {u:<3} | AggScore: {s:<6.1f} | ID: {node.id}")
    
    children = tree[node.id]
    # Sort children by their AGGREGATE score
    children.sort(key=lambda x: effective_scores[x.id], reverse=True)
    
    for child in children:
        print_node(child, indent + 1)

print(f"\nTOP HIERARCHICAL ADK TARGETS (Aggregated Score):")
print("-" * 120)

for root in roots[:10]: # Top 10 roots
    print_node(root)
