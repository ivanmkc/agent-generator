"Reader module."

import ast
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from .config import config

logger = logging.getLogger(__name__)


class SourceReader:

    def __init__(
        self, 
        repo_url: str,
        version: str = "main"
    ):
        self.repo_url = repo_url
        self.version = version
        
        # Derive a safe directory name from the repo URL
        self.repo_name = self.repo_url.split("/")[-1].replace(".git", "")
        
        # 1. Dynamic Clone Strategy
        # ~/.mcp_cache/{repo_name}/{version}
        base_dir = Path.home() / ".mcp_cache" / self.repo_name
        self.repo_root = base_dir / self.version
        
        if self.repo_root.exists():
            logger.info(f"Found existing repository clone for {self.repo_name} ({self.version}) at {self.repo_root}")
        else:
            logger.info(f"Cloning {self.repo_name} ({self.version}) from {self.repo_url} to {self.repo_root}...")
            try:
                self.repo_root.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ["git", "clone", "--depth", "1", "--branch", self.version, self.repo_url, str(self.repo_root)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info("Clone successful.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to clone repository: {e.stderr}")
                self.repo_root = None
            except Exception as e:
                logger.error(f"Unexpected error during clone: {e}")
                self.repo_root = None

    def read_source(self, rel_path: str, target_fqn: str, suffix: str = "") -> str:
        """
        Reads source code from a file, attempting to isolate the specific symbol.
        """
        if self.repo_root is None or not self.repo_root.exists():
             return f"Error: Repository {self.repo_name} ({self.version}) not found or clone failed."

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
            return f"=== File: {rel_path} (Parse Error) ===\n\n{content}"

        indexed_name = target_fqn.split(".")[-1]
        search_path = [indexed_name]
        if suffix:
            search_path.extend(suffix.split("."))

        current_scope = tree.body
        found_node = None

        for name in search_path:
            node_match = None
            for node in current_scope:
                if isinstance(
                    node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    if node.name == name:
                        node_match = node
                        break

            if node_match:
                found_node = node_match
                current_scope = node_match.body
            else:
                if found_node is None and name == indexed_name:
                    continue
                else:
                    return f"Symbol '{name}' not found in AST of {rel_path}"

        if found_node:
            lines = content.splitlines()
            start_line = found_node.lineno - 1
            if hasattr(found_node, "decorator_list") and found_node.decorator_list:
                start_line = found_node.decorator_list[0].lineno - 1

            extracted_code = "\n".join(lines[start_line:found_node.end_lineno])
            return f"=== Source: {target_fqn}{'.' + suffix if suffix else ''} ===\n\n{extracted_code}"

        return f"=== File: {rel_path} (Symbol isolation failed) ===\n\n{content}"
