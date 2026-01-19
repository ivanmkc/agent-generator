import yaml
import pytest
from pathlib import Path
from benchmarks.answer_generators.adk_tools import inspect_adk_symbol, _load_index

RANKED_TARGETS_PATH = Path("benchmarks/benchmark_generator/data/ranked_targets.yaml")

def test_ranked_targets_integrity():
    """
    Verifies that every entry in ranked_targets.yaml corresponds to a valid,
    inspectable symbol in the codebase.
    """
    if not RANKED_TARGETS_PATH.exists():
        pytest.fail(f"ranked_targets.yaml not found at {RANKED_TARGETS_PATH}")

    # Ensure index is loaded
    _load_index(str(RANKED_TARGETS_PATH))
    
    with open(RANKED_TARGETS_PATH, "r") as f:
        data = yaml.safe_load(f)
    
    assert isinstance(data, list), "ranked_targets.yaml should contain a list of entries"
    
    errors = []
    
    # Check a sample or all? All is safer but slower. 
    # There are ~1700 targets. Parsing AST for all might take a few seconds. acceptable.
    
    print(f"Verifying {len(data)} targets...")
    
    for entry in data:
        fqn = entry.get("fqn")
        if not fqn:
            errors.append(f"Entry missing FQN: {entry}")
            continue
            
        try:
            # inspect_adk_symbol returns a string. 
            # If it fails, it usually returns "Error: ..." or empty string.
            source = inspect_adk_symbol(fqn)
            
            if not source:
                errors.append(f"Empty source for {fqn}")
            elif source.startswith("Error:"):
                # Allow "No file path recorded" if it's expected for some types, 
                # but generally we want code.
                # However, adk_tools.py returns "Error: Symbol '...' not found" or "Error: ..."
                errors.append(f"Inspection failed for {fqn}: {source}")
                
        except Exception as e:
            errors.append(f"Exception inspecting {fqn}: {e}")

    if errors:
        pytest.fail(f"Found {len(errors)} errors in ranked_targets.yaml:\n" + "\n".join(errors[:20]))

if __name__ == "__main__":
    # Allow manual run
    try:
        test_ranked_targets_integrity()
        print("✅ ranked_targets.yaml is valid.")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        exit(1)
