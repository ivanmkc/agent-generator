# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A utility script to inspect Python types (classes) or modules."""

import sys
import inspect
import importlib
import argparse
import pkgutil

def get_summary(obj, max_len=300):
    """Returns a single-line summary from the object's docstring."""
    try:
        doc = inspect.getdoc(obj)
        if not doc:
            return ""
        summary = " ".join(doc.split("\n\n")[0].strip().split())
        return summary[:max_len] + "..." if len(summary) > max_len else summary
    except Exception:
        return ""

def inspect_type(fqn, obj):
    """Inspects a class object."""
    print(f"=== Type Hierarchy for {fqn} ===")
    print(f"Doc: {get_summary(obj)}")
    
    # MRO
    print("\n[Method Resolution Order (MRO)]")
    for base in inspect.getmro(obj):
        if base.__module__ != 'builtins':
            print(f"  - {base.__module__}.{base.__name__}")
        else:
            print(f"  - {base.__name__}")

    # Immediate Subclasses (if reachable/loaded)
    print("\n[Known Subclasses (Runtime)]")
    try:
        subclasses = obj.__subclasses__()
        if subclasses:
            for sub in subclasses:
                print(f"  - {sub.__module__}.{sub.__name__}")
        else:
            print("  (None loaded)")
    except Exception as e:
        print(f"  Error getting subclasses: {e}")

    # Members
    print("\n[Public Members]")
    for n, m in inspect.getmembers(obj):
        if not n.startswith("_"):
            kind = "method" if inspect.isfunction(m) or inspect.ismethod(m) else "prop" if isinstance(m, property) else "attr"
            doc = get_summary(m, max_len=100)
            doc_suffix = f": {doc}" if doc else ""
            print(f"  - {n} ({kind}){doc_suffix}")

def inspect_module(name, mod, current_depth=0, max_depth=0):
    """Recursively inspects and prints help for a module."""
    indent = "  " * current_depth
    print(f"{indent}Module: {name}")
    print(f"{indent}Doc: {get_summary(mod)}\n")

    # Inspect classes in the module
    for n, o in inspect.getmembers(mod, inspect.isclass):
        if n.startswith("_"):
            continue
        
        # Pydantic support
        fields_str = ""
        if hasattr(o, "model_fields"):
            try:
                req = [fn for fn, f in o.model_fields.items() if f.is_required()]
                opt = [fn for fn, f in o.model_fields.items() if not f.is_required()]
                fields_str = f" [Pydantic Model - Required: {req}, Optional: {opt}]"
            except Exception:
                pass

        try:
            sig = inspect.signature(o)
        except Exception:
            sig = "(...)"

        # Get base classes
        bases = []
        for b in o.__bases__:
            if b.__module__ != 'builtins':
                bases.append(b.__name__)
        bases_str = f"({', '.join(bases)})" if bases else ""

        print(f"{indent}  class {n}{bases_str}{sig}{fields_str}: {get_summary(o)}")

        # Inspect methods in the class
        methods = [
            (mn, mo)
            for mn, mo in inspect.getmembers(o)
            if (not mn.startswith("_") or mn == "__init__") 
            and (inspect.isfunction(mo) or inspect.ismethod(mo))
        ]
        # Show __init__ first, then others alphabetically, limit to 5
        for mn, mo in sorted(methods, key=lambda x: (0 if x[0] == "__init__" else 1, x[0]))[:5]:
            try:
                msig = inspect.signature(mo)
            except Exception:
                msig = "(...)"
            print(f"{indent}    def {mn}{msig}")

    # Recursive step for submodules
    if current_depth < max_depth and hasattr(mod, "__path__"):
        try:
            for _, subname, _ in pkgutil.iter_modules(mod.__path__):
                if not subname.startswith("_"):
                    inspect_module(f"{name}.{subname}", importlib.import_module(f"{name}.{subname}"), current_depth + 1, max_depth)
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="Inspect a Python object (class or module).")
    parser.add_argument("fqn", help="Fully qualified name of the object (e.g. google.adk.agents.LlmAgent)")
    parser.add_argument("--depth", type=int, default=0, help="Recursion depth for modules.")
    args = parser.parse_args()

    # Try to import as module first
    try:
        obj = importlib.import_module(args.fqn)
        inspect_module(args.fqn, obj, max_depth=args.depth)
        return
    except ImportError:
        pass

    # Try as class/member
    try:
        module_name, class_name = args.fqn.rsplit(".", 1)
        mod = importlib.import_module(module_name)
        obj = getattr(mod, class_name)
        
        if inspect.isclass(obj):
            inspect_type(args.fqn, obj)
        elif inspect.ismodule(obj):
             inspect_module(args.fqn, obj, max_depth=args.depth)
        else:
             print(f"Object '{args.fqn}' is {type(obj)}, not a class or module. Simple inspection:")
             print(f"Doc: {get_summary(obj)}")
             print(f"Value: {obj}")

    except (ValueError, ImportError, AttributeError) as e:
        print(f"Error: Could not load '{args.fqn}'.\nDetails: {e}")

if __name__ == "__main__":
    main()
