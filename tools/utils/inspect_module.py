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

"""A utility script to inspect Python modules and print a summary of their API."""

import sys
import inspect
import pkgutil
import importlib
import argparse


def get_summary(obj, max_len=300):
    """Returns a single-line summary from the object's docstring."""
    doc = inspect.getdoc(obj)
    if not doc:
        return ""
    # Take the first paragraph and collapse whitespace
    summary = " ".join(doc.split("\n\n")[0].strip().split())
    if len(summary) > max_len:
        return summary[: max_len - 3] + "..."
    return summary


def print_help(name, current_depth=0, max_depth=0):
    """Recursively inspects and prints help for a module and its submodules."""
    indent = "  " * current_depth
    try:
        mod = importlib.import_module(name)
    except Exception:
        # Silently skip modules that fail to import
        return

    print(f"{indent}Module: {name}")
    print(f"{indent}Doc: {get_summary(mod)}\n")

    # Inspect classes in the module
    for n, o in inspect.getmembers(mod, inspect.isclass):
        if n.startswith("_"):
            continue
        
        # Check if class is defined in this module (not imported)
        if getattr(o, "__module__", "") != name:
             # Optional: we might still want to show it if it's a re-export
             if not name.endswith(".__init__") and not getattr(mod, "__file__", "").endswith("__init__.py"):
                 # continue # Skip for now to reduce noise if not in __init__
                 pass

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

        print(f"{indent}  class {n}{sig}{fields_str}: {get_summary(o)}")

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

        # Inspect properties
        props = [
            (pn, po)
            for pn, po in inspect.getmembers(o)
            if isinstance(po, property) and not pn.startswith("_")
        ]
        for pn, po in sorted(props)[:5]:
            print(f"{indent}    @property {pn}")

    # Recursive step for submodules
    if current_depth < max_depth and hasattr(mod, "__path__"):
        try:
            for _, subname, _ in pkgutil.iter_modules(mod.__path__):
                if not subname.startswith("_"):
                    print_help(f"{name}.{subname}", current_depth + 1, max_depth)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Inspect a Python module.")
    parser.add_argument("module_name", help="Name of the module to inspect.")
    parser.add_argument(
        "--depth", type=int, default=0, help="Recursion depth for submodules."
    )
    args = parser.parse_args()

    print_help(args.module_name, 0, args.depth)


if __name__ == "__main__":
    main()
