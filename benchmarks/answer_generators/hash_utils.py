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

"""Utility functions for source code hashing."""

import fnmatch
import hashlib
import os
from pathlib import Path


def calculate_source_hash(directory: Path) -> str:
    """Calculates a deterministic hash of the source directory."""
    sha = hashlib.sha256()

    # Try to read .gitignore
    ignore_patterns = [
        ".git",
        "__pycache__",
        ".ipynb_checkpoints",
        "node_modules",
        "venv",
        "version.txt",  # Added to default ignores
        "package-lock.json",  # Added to default ignores
        "npm-debug.log",  # Added to default ignores
    ]
    gitignore_path = directory / ".gitignore"
    if gitignore_path.exists():
        try:
            with open(gitignore_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        ignore_patterns.append(line)
        except Exception:
            pass  # Ignore errors reading .gitignore

    for root, dirs, files in os.walk(directory):
        # Sort in-place to ensure deterministic walk order
        dirs.sort()
        files.sort()

        # Prune ignored dirs
        i = 0
        while i < len(dirs):
            d = dirs[i]
            rel_path = (Path(root) / d).relative_to(directory).as_posix()

            should_ignore = False
            # Check against simple name matches first (common case)
            if d in ignore_patterns:
                should_ignore = True
            else:
                # Check patterns
                for pattern in ignore_patterns:
                    if fnmatch.fnmatch(d, pattern) or fnmatch.fnmatch(
                        rel_path, pattern
                    ):
                        should_ignore = True
                        break

            if should_ignore:
                del dirs[i]
            else:
                i += 1

        for file in files:
            rel_path = (Path(root) / file).relative_to(directory).as_posix()
            should_ignore = False
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(file, pattern) or fnmatch.fnmatch(rel_path, pattern):
                    should_ignore = True
                    break

            if should_ignore:
                continue

            path = Path(root) / file
            # Hash path (relative) and content
            sha.update(rel_path.encode())
            try:
                with open(path, "rb") as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        sha.update(chunk)
            except OSError:
                pass  # Skip if unreadable
    return sha.hexdigest()
