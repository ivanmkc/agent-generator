import yaml
import json
import sys
from pathlib import Path
from collections import defaultdict

def main():
    root_module = "google.adk.agents"
    stats_path = "benchmarks/adk_stats.yaml"
    coocc_path = "benchmarks/data_science_stats.json"
    
    # Load Data
    structure = {}
    if Path(stats_path).exists():
        with open(stats_path, "r") as f:
            structure = yaml.safe_load(f)
            
    associations = []
    if Path(coocc_path).exists():
        with open(coocc_path, "r") as f:
            associations = json.load(f).get("associations", [])

    # Build Graph: Context -> [Targets]
    graph = defaultdict(list)
    for assoc in associations:
        if assoc["probability"] > 0.1: # Threshold
            graph[assoc["context"]].append(assoc["target"])

    print(f"ROOT: {root_module}")
    visited = set()

    def print_tree(node, indent=0):
        if node in visited: return
        visited.add(node)
        
        prefix = "  " * indent
        # Print Node
        print(f"{prefix}📦 {node}")
        
        # 1. Structural Children (Classes/Methods inside this module)
        # Scan adk_stats for keys starting with node + "."
        children = []
        for key, data in structure.items():
            if key.startswith(node + ".") and key.count(".") == node.count(".") + 1:
                children.append((key, data))
        
        for child_key, data in children:
            child_name = child_key.split(".")[-1]
            icon = "©️" if child_name[0].isupper() else "ƒ"
            print(f"{prefix}  {icon} {child_name}")
            
            # Parameters
            args = data.get("args", {})
            for arg, arg_data in args.items():
                print(f"{prefix}    🔹 {arg}")

        # 2. Associated Modules (Co-occurrence)
        # Find neighbors in the association graph
        neighbors = graph.get(node, [])
        if neighbors:
            print(f"{prefix}  🔗 Co-occurs with:")
            for neighbor in neighbors:
                if neighbor not in visited:
                    print_tree(neighbor, indent + 2)

    print_tree(root_module)

if __name__ == "__main__":
    main()
