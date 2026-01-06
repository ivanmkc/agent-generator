import pkgutil
import inspect
import importlib
import os
import sys
from pathlib import Path

# Ensure env site-packages is in path
env_site_packages = Path("env/lib/python3.13/site-packages")
if env_site_packages.exists():
    sys.path.insert(0, str(env_site_packages.resolve()))

import google.adk

def generate_index(package, prefix="google.adk"):
    index_lines = ["# ADK Python Library Index", "", "This index maps module paths to their descriptions.", ""]
    
    # Walk the package
    path = package.__path__
    prefix_len = len(prefix) + 1

    for finder, name, ispkg in pkgutil.walk_packages(path, prefix + "."):
        try:
            module = importlib.import_module(name)
            
            # Skip private modules unless relevant? 
            # ADK has many private modules. We might want to skip `_` prefixed ones unless they are core flows.
            if "._" in name and not ".flows." in name: 
                 # Heuristic: skip private utils, but keep private flow implementations if they are important?
                 # Actually, usually users only import public modules.
                 pass
            
            # Get docstring
            doc = inspect.getdoc(module)
            summary = doc.split('\n')[0] if doc else "No description available."
            
            # List exported classes/functions (defined in __all__ or strictly public)
            exports = []
            if hasattr(module, "__all__"):
                exports = module.__all__
            else:
                for member_name, member in inspect.getmembers(module):
                    if not member_name.startswith("_") and (inspect.isclass(member) or inspect.isfunction(member)):
                        if member.__module__ == name: # Only include locally defined things
                            exports.append(member_name)
            
            if exports:
                index_lines.append(f"## `{name}`")
                index_lines.append(f"{summary}")
                index_lines.append(f"**Exports:** {', '.join(exports)}")
                index_lines.append("")
                
        except Exception as e:
            print(f"Skipping {name}: {e}")
            continue

    return "\n".join(index_lines)

if __name__ == "__main__":
    index_content = generate_index(google.adk)
    output_path = Path("benchmarks/adk_index.md")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        f.write(index_content)
    print(f"Index generated at {output_path}")
