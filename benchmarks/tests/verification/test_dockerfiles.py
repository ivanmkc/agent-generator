import pytest
import os
from pathlib import Path
import re

# Define the project root relative to this test file
# benchmarks/tests/verification/test_dockerfiles.py -> benchmarks/tests/verification -> benchmarks/tests -> benchmarks -> root
PROJECT_ROOT = Path(__file__).resolve().parents[3]

def find_dockerfiles(root_dir):
    """Recursively find all Dockerfiles."""
    dockerfiles = []
    for path in root_dir.rglob("Dockerfile"):
        if "node_modules" not in str(path) and ".git" not in str(path):
            dockerfiles.append(path)
    return dockerfiles

def test_dockerfile_copy_paths_exist():
    """
    Parses all Dockerfiles in the repository and verifies that local source paths
    in COPY commands actually exist on the filesystem.
    """
    dockerfiles = find_dockerfiles(PROJECT_ROOT)
    
    errors = []
    
    for dockerfile in dockerfiles:
        content = dockerfile.read_text()
        # Match COPY <src> <dest>
        # This regex is simple and might need refinement for complex multi-stage or array-syntax COPY
        # COPY ["src", "dest"] is also valid but less common in this repo
        # We assume standard 'COPY src dest' format for now
        matches = re.findall(r'^COPY\s+([^\s]+)\s+', content, re.MULTILINE)
        
        for src_path_str in matches:
            # Ignore flags like --from=...
            if src_path_str.startswith("--"):
                continue
                
            # If path is absolute, it's relative to the build context root (usually repo root)
            # If path is relative, it's relative to the Dockerfile's directory?
            # NO, Docker COPY src is always relative to the build context.
            # In this project, build context is almost always the project root.
            
            # We assume build context is PROJECT_ROOT
            expected_path = PROJECT_ROOT / src_path_str
            
            if not expected_path.exists():
                # Try relative to Dockerfile just in case context is different (rare here)
                relative_path = dockerfile.parent / src_path_str
                if not relative_path.exists():
                     errors.append(f"Dockerfile: {dockerfile.relative_to(PROJECT_ROOT)}\n  Missing COPY source: {src_path_str}")

    assert not errors, "\n".join(errors)
