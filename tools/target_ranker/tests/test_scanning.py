"""Test Scanning module."""

import os
import json
import pytest
import shutil
from pathlib import Path
from tools.target_ranker.scanner import scan_repository
from google.adk.tools import ToolContext
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.base_agent import BaseAgent


class MockAgent(BaseAgent):

    async def _run_async_impl(self, ctx: InvocationContext):
        if False:
            yield None


@pytest.fixture
def temp_repo(tmp_path):
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Create a dummy package
    pkg_dir = repo_dir / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()

    # Create a class with __init__
    code = """
class MyClass:
    def __init__(self, x: int):
        self.x = x

    def public_method(self):
        pass
"""
    with open(pkg_dir / "module.py", "w") as f:
        f.write(code)

    return repo_dir


@pytest.mark.asyncio
async def test_scan_repository_captures_init(temp_repo):
    # Setup context
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        session_id="test", user_id="user", app_name="app"
    )

    inv_context = InvocationContext(
        invocation_id="test_inv",
        agent=MockAgent(name="test_agent"),
        session=session,
        session_service=session_service,
    )

    tool_context = ToolContext(
        invocation_context=inv_context,
        function_call_id="call_id",
        event_actions=None,
        tool_confirmation=None,
    )

    session.state["target_namespace"] = "pkg"
    session.state["stats_file_path"] = "nonexistent.yaml"  # No stats needed

    # Run scan
    scan_repository(str(temp_repo), tool_context, namespace="pkg")

    structure_map = session.state["structure_map"]

    # Verify MyClass is found
    class_fqn = "pkg.module.MyClass"
    assert class_fqn in structure_map, f"Structure map keys: {structure_map.keys()}"

    # Verify __init__ is in children
    children = structure_map[class_fqn]["children"]
    init_fqn = f"{class_fqn}.__init__"

    # This assertion is expected to fail currently
    assert init_fqn in children, f"__init__ not found in children: {children}"

    # Verify TargetRanker picks it up
    from tools.target_ranker.ranker import TargetRanker

    # Create entity map for ranker
    entity_map = {e["id"]: e for e in session.state["scanned_targets"]}

    ranker = TargetRanker(repo_path=str(temp_repo))

    # We need to manually build adk_inheritance since we aren't running ranker.generate()
    # For this simple test, empty inheritance is fine as MyClass has no bases
    adk_inheritance = {}

    sig = ranker.reconstruct_constructor_signature(
        class_fqn, structure_map, entity_map, adk_inheritance
    )

    # Should match the defined __init__
    # Synthetic one would be "def __init__(self, *, x: int):"
    # Real one is "def __init__(self, x: int):" -> resolved signature might look slightly different depending on resolution

    assert sig is not None, "Signature should not be None if __init__ exists"
    assert "x: int" in sig
    assert "*" not in sig, f"Should not be keyword-only (synthetic). Got: {sig}"
