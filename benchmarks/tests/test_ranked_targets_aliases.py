import sys
import yaml
import pytest
import importlib
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RANKED_TARGETS_PATH = PROJECT_ROOT / "benchmarks/generator/benchmark_generator/data/ranked_targets.yaml"

def get_object_from_fqn(fqn):
    """
    Dynamically imports a module and retrieves an object by its Fully Qualified Name (FQN).
    """
    try:
        parts = fqn.split('.')
        module_name = ".".join(parts[:-1])
        obj_name = parts[-1]
        
        # Handle cases where the FQN is just a module
        try:
            module = importlib.import_module(fqn)
            return module
        except ImportError:
            pass

        # Handle class/function in a module
        module = importlib.import_module(module_name)
        return getattr(module, obj_name)
    except (ImportError, AttributeError, ValueError):
        return None

def test_ranked_targets_aliases_identity():
    """
    Verifies that for every entry in ranked_targets.yaml with an 'aliases' field,
    each alias points to the EXACT SAME Python object (in memory) as the canonical ID.
    
    This ensures that our alias detection logic is correct and we aren't aliasing 
    unrelated objects.
    """
    if not RANKED_TARGETS_PATH.exists():
        pytest.fail(f"ranked_targets.yaml not found at {RANKED_TARGETS_PATH}")

    with open(RANKED_TARGETS_PATH, "r") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, list), "ranked_targets.yaml should contain a list of entries"

    checked_count = 0
    errors = []

    print(f"\nVerifying aliases for {len(data)} targets...")

    for entry in data:
        aliases = entry.get("aliases")
        if not aliases:
            continue

        canonical_id = entry.get("id")
        if not canonical_id:
            errors.append(f"Entry with aliases missing ID: {entry}")
            continue

        # Load canonical object
        canonical_obj = get_object_from_fqn(canonical_id)
        if canonical_obj is None:
            continue

        for alias in aliases:
            # Load alias object
            alias_obj = get_object_from_fqn(alias)
            
            if alias_obj is None:
                errors.append(f"Could not load alias object: {alias} (for {canonical_id})")
                continue

            # Verify Identity
            if alias_obj is not canonical_obj:
                errors.append(
                    f"Identity Mismatch for {canonical_id}:\n"
                    f"  Canonical: {canonical_obj}\n"
                    f"  Alias:     {alias_obj} ({alias})\n"
                    f"  (They are different objects in memory)"
                )
            
            checked_count += 1

    if errors:
        pytest.fail(
            f"Found {len(errors)} alias identity errors:\n" + "\n".join(errors[:20])
        )

    print(f"✅ Verified {checked_count} aliases across {len(data)} targets.")

if __name__ == "__main__":
    # Allow running directly for quick checks
    sys.exit(pytest.main(["-v", __file__]))