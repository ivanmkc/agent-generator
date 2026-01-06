"""
Tests for the ADK Index YAML file.
Verifies that the index structure is valid and that all referenced modules and exports 
can be imported in the current environment.
"""

import pytest
import yaml
import importlib
from pathlib import Path
import sys

# Add project root to sys.path to ensure we can run this from anywhere
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

def test_adk_index_validity():
    # Locate index relative to this test file
    index_path = project_root / "benchmarks/adk_index.yaml"
    
    if not index_path.exists():
        pytest.fail(f"Index file not found at {index_path}")

    with open(index_path, "r") as f:
        data = yaml.safe_load(f)

    assert "modules" in data, "YAML must contain 'modules' key"
    
    for module_entry in data["modules"]:
        path = module_entry["path"]
        exports = module_entry.get("exports", [])
        
        print(f"Testing module: {path}")
        
        # 1. Verify Import
        try:
            mod = importlib.import_module(path)
        except ImportError as e:
            pytest.fail(f"Failed to import module '{path}': {e}")
            
        # 2. Verify Exports
        for export_name in exports:
            if not hasattr(mod, export_name):
                # Check if it's available via __all__ if defined
                if hasattr(mod, "__all__") and export_name in mod.__all__:
                    continue # It's exported via __all__, might be lazy loaded or dynamic
                pytest.fail(f"Module '{path}' does not export '{export_name}'")

if __name__ == "__main__":
    # Allow running directly
    try:
        test_adk_index_validity()
        print("All modules verified successfully!")
    except Exception as e:
        print(f"Verification failed: {e}")
        exit(1)
