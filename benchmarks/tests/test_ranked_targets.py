"""Test Ranked Targets module."""

import yaml
import pytest
from pathlib import Path
import ast
import sys

# Add root to sys.path for core imports
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from core.config import RANKED_TARGETS_FILE

RANKED_TARGETS_PATH = RANKED_TARGETS_FILE
REPO_ROOT = Path("repos/adk-python")


def test_ranked_targets_integrity():
    """
    Verifies that every entry in ranked_targets.yaml corresponds to a valid,
    inspectable symbol in the codebase.
    """
    if not RANKED_TARGETS_PATH.exists():
        pytest.fail(f"ranked_targets.yaml not found at {RANKED_TARGETS_PATH}")

    with open(RANKED_TARGETS_PATH, "r") as f:
        data = yaml.safe_load(f)

    assert isinstance(
        data, list
    ), "ranked_targets.yaml should contain a list of entries"

    errors = []

    print(f"Verifying {len(data)} targets...")

    for entry in data:
        fqn = entry.get("id") or entry.get("fqn")
        if not fqn:
            errors.append(f"Entry missing FQN/ID: {entry}")
            continue

        rel_path = entry.get("file_path")
        if not rel_path:
            # Some entries might not have file_path if they are module-level?
            # But we want them for inspection.
            errors.append(f"No file_path for {fqn}")
            continue

        # Check for signature on methods
        if entry.get("type") in ["METHOD", "Method"]:
            if not entry.get("signature"):
                errors.append(f"Missing signature for method: {fqn}")

        full_path = REPO_ROOT / rel_path
        
        # Skip external dependencies if env is missing
        if rel_path.startswith("env/"):
            if not full_path.exists():
                # Just warn/skip if we are not in the same env
                continue

        if not full_path.exists():
            # Fallback 1: Try adding src/ prefix (common python layout)
            src_path = REPO_ROOT / "src" / rel_path
            if src_path.exists():
                full_path = src_path
            else:
                # Fallback 2: Check if it's relative to workspace root (for external deps like env/lib/...)
                full_path = Path(rel_path)
                if not full_path.exists():
                    errors.append(f"File not found for {fqn}: {rel_path}")
                    continue

        # Try to parse and find the symbol
        if entry.get("type") == "MODULE":
            continue  # Just verify file exists for modules

        try:
            content = full_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            target_name = fqn.split(".")[-1]

            found = False
            for node in tree.body:
                if isinstance(
                    node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    if node.name == target_name:
                        found = True
                        break

            if not found:
                # Fallback check for constants or imports
                if target_name not in content:
                    errors.append(
                        f"Symbol {target_name} not found in {rel_path} for {fqn}"
                    )
        except Exception as e:
            errors.append(f"Exception parsing {rel_path} for {fqn}: {e}")

    if errors:
        pytest.fail(
            f"Found {len(errors)} errors in ranked_targets.yaml:\n"
            + "\n".join(errors[:20])
        )


if __name__ == "__main__":
    # Allow manual run
    try:
        test_ranked_targets_integrity()
        print("✅ ranked_targets.yaml is valid.")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        exit(1)
