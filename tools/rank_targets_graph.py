import ast
import os
import json
import yaml
import sys
from pathlib import Path
from collections import defaultdict, Counter

# Add root to sys.path
sys.path.append(os.getcwd())

from benchmarks.benchmark_generator.models import TargetEntity, TargetType

def get_physical_structure(repo_path):
    """Scans the repo to build a map of FQN -> Definition metadata (including Constants)."""
    root_dir = Path(repo_path).resolve()
    node_map = {}
    ignored_dirs = {'.git', '.vscode', '.gemini', '__pycache__', 'env', 'venv', 'node_modules', 'dist', 'build'}
    
    python_files = []
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
            
            if not module_fqn.startswith("google.adk"): continue

            with open(full_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            node_map[module_fqn] = {
                "type": "module",
                "name": module_parts[-1],
                "children": [],
                "params": {},
                "constants": []
            }

            class StructVisitor(ast.NodeVisitor):
                def __init__(self, mod_fqn):
                    self.current_class_fqn = None
                    self.mod_fqn = mod_fqn

                def visit_ClassDef(self, node):
                    if node.name.startswith("_"): return
                    class_fqn = f"{self.mod_fqn}.{node.name}"
                    node_map[class_fqn] = {
                        "type": "class",
                        "name": node.name,
                        "children": [],
                        "params": {},
                        "constants": []
                    }
                    node_map[self.mod_fqn]["children"].append(class_fqn)
                    
                    old = self.current_class_fqn
                    self.current_class_fqn = class_fqn
                    self.generic_visit(node)
                    self.current_class_fqn = old

                def visit_FunctionDef(self, node):
                    if node.name.startswith("_") and node.name != "__init__": return
                    parent_fqn = self.current_class_fqn or self.mod_fqn
                    func_fqn = f"{parent_fqn}.{node.name}"
                    
                    params = {}
                    for arg in node.args.args:
                        if arg.arg == "self": continue
                        t_hint = "Any"
                        if arg.annotation:
                            try: t_hint = ast.unparse(arg.annotation)
                            except: pass
                        params[arg.arg] = t_hint

                    node_map[func_fqn] = {
                        "type": "method",
                        "name": node.name,
                        "children": [],
                        "params": params,
                        "constants": []
                    }
                    node_map[parent_fqn]["children"].append(func_fqn)

                def visit_Assign(self, node):
                    # Capture constants (CAPS_NAME)
                    parent_fqn = self.current_class_fqn or self.mod_fqn
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                             node_map[parent_fqn]["constants"].append(target.id)

                def visit_AnnAssign(self, node):
                    # Capture annotated constants
                    parent_fqn = self.current_class_fqn or self.mod_fqn
                    if isinstance(node.target, ast.Name) and node.target.id.isupper():
                         node_map[parent_fqn]["constants"].append(node.target.id)

            StructVisitor(module_fqn).visit(tree)
        except Exception: pass
    return node_map

def main():
    root_module = "google.adk.agents"
    stats_path = "benchmarks/adk_stats.yaml"
    coocc_path = "benchmarks/adk_cooccurrence.json"
    repo_path = "../adk-python"
    
    structure = get_physical_structure(repo_path)
    
    usage_stats = {}
    if Path(stats_path).exists():
        with open(stats_path, "r") as f:
            usage_stats = yaml.safe_load(f)
            
    associations = []
    support_counts = Counter()
    if Path(coocc_path).exists():
        with open(coocc_path, "r") as f:
            data = json.load(f)
            associations = data.get("associations", [])
            for a in associations:
                support_counts[a["context"]] = max(support_counts[a["context"]], a["support"] / a["probability"] if a["probability"] > 0 else 0)
                support_counts[a["target"]] = max(support_counts[a["target"]], a["support"])

    assoc_graph = defaultdict(list)
    for a in associations:
        assoc_graph[a["context"]].append((a["target"], a["probability"], a["support"]))

    visited = set()
    visible_nodes = set()
    
    def check_visibility(node_fqn):
        node = structure.get(node_fqn)
        if not node: return False
        
        calls = usage_stats.get(node_fqn, {}).get("total_calls", 0)
        imports = int(support_counts[node_fqn])
        is_visible = (calls > 0 or imports > 0)
        
        for child in node["children"]:
            if check_visibility(child):
                is_visible = True
        
        # Check params usage
        p_stats = usage_stats.get(node_fqn, {}).get("args", {})
        if any(p_data.get("count", 0) > 0 for p_data in p_stats.values()):
            is_visible = True

        if is_visible:
            visible_nodes.add(node_fqn)
        return is_visible

    for fqn, data in structure.items():
        if data["type"] == "module":
            check_visibility(fqn)
    
    visible_nodes.add(root_module)

    def print_node(node_fqn, indent=0, label=""):
        if node_fqn not in visible_nodes and "Unwrapped" not in label and "Prob" not in label and node_fqn != root_module:
            return

        if node_fqn in visited:
            print(f"{ '  '*indent}↪️ {node_fqn} (Already shown above)")
            return
        
        node = structure.get(node_fqn)
        if not node:
            if "." in node_fqn:
                 print(f"{ '  '*indent}📦 {node_fqn} {label}")
            return

        visited.add(node_fqn)
        
        calls = usage_stats.get(node_fqn, {}).get("total_calls", 0)
        imports = int(support_counts[node_fqn])
        usage_str = f"C:{calls}/I:{imports}"
        
        prefix = "  " * indent
        icon = "📦" if node["type"] == "module" else "©️" if node["type"] == "class" else "ƒ"
        
        print(f"{prefix}{icon} {node['name']:<30} | Usage: {usage_str:<10} {label}")

        # Constants
        for const in node.get("constants", []):
            print(f"{prefix}  🔸 {const}")

        # Parameters & Type Unwrapping
        if node["params"]:
            p_stats = usage_stats.get(node_fqn, {}).get("args", {})
            # Sort params by usage
            sorted_params = sorted(node["params"].items(), key=lambda x: p_stats.get(x[0], {}).get("count", 0), reverse=True)
            
            for p_name, p_type in sorted_params:
                p_usage = p_stats.get(p_name, {}).get("count", 0)
                
                # Filter: Omit 0 usage params if requested, but usually good for context.
                # User said "omit 0 usage in display". For params, let's keep only used ones.
                if p_usage == 0: continue

                print(f"{prefix}  🔹 {p_name:<20} | Type: {p_type:<20} | Usage: {p_usage}")
                
                # RECURSIVE UNWRAP
                for word in p_type.replace("[", " ").replace("]", " ").replace("|", " ").split():
                    target_type_fqn = None
                    if word in structure: target_type_fqn = word
                    else:
                        for fqn, data in structure.items():
                            if data["name"] == word and data["type"] == "class":
                                target_type_fqn = fqn
                                break
                    if target_type_fqn and target_type_fqn != node_fqn:
                        print_node(target_type_fqn, indent + 3, label=f"(Type of param '{p_name}')")

        # Children (Sorted by Usage)
        child_fqns = node["children"]
        child_fqns.sort(key=lambda x: usage_stats.get(x, {}).get("total_calls", 0) + support_counts[x], reverse=True)
        for cfqn in child_fqns:
            print_node(cfqn, indent + 1)

        # Associations
        neighbors = assoc_graph.get(node_fqn, [])
        if "." in node_fqn:
             mod_fqn = ".".join(node_fqn.split(".")[:3]) 
             neighbors.extend(assoc_graph.get(mod_fqn, []))
             seen = set()
             unique_neighbors = []
             for n in neighbors:
                 if n[0] not in seen:
                     unique_neighbors.append(n)
                     seen.add(n[0])
             neighbors = unique_neighbors

        neighbors.sort(key=lambda x: x[1], reverse=True) 
        if neighbors and indent < 4:
            for neighbor, prob, count in neighbors:
                if prob > 0.05 and neighbor not in visited:
                    print_node(neighbor, indent + 1, label=f"🔗 (Prob: {prob:.2f})")

    print(f"\nADK HIERARCHICAL ASSOCIATION GRAPH (Granular Detail)")
    print("-" * 140)
    print_node(root_module)

if __name__ == "__main__":
    main()