import ast
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class SourceReader:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def read_source(self, rel_path: str, target_fqn: str, suffix: str = "") -> str:
        """
        Reads source code from a file, attempting to isolate the specific symbol.
        """
        if rel_path.startswith("env/"):
             # Fallback for Docker envs where env/ is at /workdir/env (heuristic)
             full_path = Path("/workdir") / rel_path
             if not full_path.exists():
                 # Or check if it's relative to REPO_ROOT (rare for env/)
                 full_path = self.repo_root / rel_path
        else:
            full_path = self.repo_root / rel_path

        if not full_path.exists():
            return f"File not found on disk: {full_path}"

        try:
            content = full_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fallback for non-python files or parse errors
            return f"=== File: {rel_path} (Parse Error) ===\n\n{content}"

        # Determine the AST search path
        # If target_fqn is 'a.b.C' and suffix is 'm', search path is ['C', 'm'] usually.
        # But if 'a.b' is the module, we search for 'C' then 'm'.
        # The 'target_fqn' is the ID of the INDEXED item (e.g. the class).
        # We assume the indexed item's name is the last part of its FQN.
        
        indexed_name = target_fqn.split(".")[-1]
        search_path = [indexed_name]
        if suffix:
            search_path.extend(suffix.split("."))
            
        current_scope = tree.body
        found_node = None
        
        for name in search_path:
            node_match = None
            for node in current_scope:
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == name:
                        node_match = node
                        break
            
            if node_match:
                found_node = node_match
                current_scope = node_match.body
            else:
                 # Special case: If the first item wasn't found, maybe the file IS the module 
                 # and we should look for the suffix directly in the root scope?
                 # (e.g. FQN=module, name=module_name, but file defines class X)
                 if found_node is None and name == indexed_name:
                     continue
                 else:
                     return f"Symbol '{name}' not found in AST of {rel_path}"

        if found_node:
            lines = content.splitlines()
            start_line = found_node.lineno - 1
            if hasattr(found_node, 'decorator_list') and found_node.decorator_list:
                start_line = found_node.decorator_list[0].lineno - 1
            
            end_line = found_node.end_lineno
            extracted_code = "\n".join(lines[start_line:end_line])
            return f"=== Source: {target_fqn}{'.' + suffix if suffix else ''} ===\n\n{extracted_code}"
        
        return f"=== File: {rel_path} (Symbol isolation failed) ===\n\n{content}"
