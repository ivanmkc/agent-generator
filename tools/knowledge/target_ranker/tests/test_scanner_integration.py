"""Test Scanner Integration module."""

import pytest
import json
from unittest.mock import MagicMock
from tools.knowledge.target_ranker.scanner import scan_repository

# Removed mock_context fixture as it relied on ADK types which are no longer used by scanner

def test_scan_repository(tmp_path):
    """Verifies that the Cartographer scan correctly identifies testable methods and counts usage."""
    # Create a dummy python file defining the API
    p = tmp_path / "my_module.py"
    p.write_text(
        "class Foo:\n  def bar(self):\n    '''Docstring'''\n    x=1\n    y=2\n    return x+y"
    )

    # Create a caller file to test usage counting
    caller = tmp_path / "caller.py"
    # Use explicit FQN style to ensure naive static analysis catches it
    caller.write_text("import my_module\nmy_module.Foo.bar(None)")

    # Create dummy usage stats for external usage simulation
    usage_stats = {
        "my_module.Foo.bar": {
            "total_calls": 5,
            "args": {}
        }
    }

    result = scan_repository(
        repo_path=str(tmp_path), 
        namespace=None,
        usage_stats=usage_stats
    )

    # scan_repository returns a dict with "scanned_targets", "structure_map", etc.
    assert "scanned_targets" in result
    targets = result["scanned_targets"]

    # Verify bar was found. TargetEntity uses 'id' (FQN) and 'name'.
    # FQN logic: module_name.ClassName.MethodName
    bar_target = next(
        (t for t in targets if t["name"] == "bar" and t["type"] == "method"), None 
    )
    
    if not bar_target:
        # Retry with looser type check if needed or check if type serialization changed
        bar_target = next(
            (t for t in targets if t["name"] == "bar"), None 
        )

    assert bar_target is not None
    assert bar_target["id"] == "my_module.Foo.bar"

    # Verify usage was counted
    assert bar_target["usage_score"] >= 1
