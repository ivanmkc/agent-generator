"""Test Scanner Integration module."""

import pytest
import json
from unittest.mock import MagicMock
from google.adk.tools import ToolContext
from google.adk.sessions import Session
from tools.knowledge.target_ranker.scanner import scan_repository


@pytest.fixture
def mock_context():
    """Provides a mocked ToolContext with an initialized Session for tool testing."""
    session = Session(id="test_session", appName="benchmark_test", userId="test_user")
    ctx = MagicMock(spec=ToolContext)
    ctx.session = session
    return ctx


def test_scan_repository(mock_context, tmp_path):
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
    stats_file = tmp_path / "adk_stats.yaml"
    stats_file.write_text("my_module.Foo.bar:\n  total_calls: 5\n  args: {}")
    mock_context.session.state["stats_file_path"] = str(stats_file)

    result = scan_repository(str(tmp_path), mock_context)

    assert "Cartographer scan complete" in result
    targets = mock_context.session.state["scanned_targets"]

    # Verify bar was found. TargetEntity uses 'id' (FQN) and 'name'.
    # FQN logic in tools.py: module_name.ClassName.MethodName
    # module_name is 'my_module'
    bar_target = next(
        (t for t in targets if t["name"] == "bar" and t["type"] == "method"), None
    )
    assert bar_target is not None
    assert bar_target["id"] == "my_module.Foo.bar"

    # Verify usage was counted
    # Usage counting logic depends on 'adk_stats.yaml' being loaded.
    # scan_repository loads usage_stats from 'stats_file_path' in session state.
    # The test sets it.
    # However, scan_repository also does a runtime usage check?
    # "Pre-load usage stats into memory map... runtime_usage_map"
    # It imports the module.
    # For this to work, tmp_path must be in sys.path?
    # scan_repository does: sys.path.insert(0, str(root_dir))
    # So it should work.

    # Note: TargetRanker (static) logic might get 5 from yaml.
    # Runtime logic might check actual calls? No, runtime logic loads stats from yaml and then checks if object exists in memory.
    # It doesn't count calls dynamically during scan (that would require execution).
    # It counts "total_calls" from stats file if object matches.

    assert bar_target["usage_score"] >= 1
