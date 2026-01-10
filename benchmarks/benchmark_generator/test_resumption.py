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

"""
Integration tests for the Prismatic Generator's state persistence.

This module simulates system crashes and process restarts to verify that
the SqliteSessionService correctly preserves the generation state, allowing
the generator to resume exactly where it left off.
"""

import pytest
import json
from unittest.mock import MagicMock
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.adk.tools import ToolContext
from benchmarks.benchmark_generator.tools import get_prioritized_target

@pytest.mark.asyncio
async def test_session_resumption(tmp_path):
    """
    Simulates a crash and restart cycle.
    
    1. Creates a session and populates it with targets and progress.
    2. Destroys the session service instance (simulating a crash).
    3. Creates a new service instance pointing to the same DB.
    4. Verifies that progress is restored and the next target is correctly selected.
    """
    db_path = str(tmp_path / "test_session.db")
    session_id = "test_run_1"
    user_id = "user_1"
    app_name = "test_app"

    # --- Phase 1: Initial Run ---
    service1 = SqliteSessionService(db_path=db_path)
    
    # Initialize targets and a state where one target is already processed
    targets = [
        {"file_path": "a.py", "method_name": "method_A", "complexity_score": 10, "docstring": None},
        {"file_path": "b.py", "method_name": "method_B", "complexity_score": 10, "docstring": None}
    ]
    initial_state = {
        "scanned_targets": targets,
        "processed_targets_list": ["a.py::method_A"],
        "generated_benchmarks": [{"id": "bench_A"}]
    }
    
    # Persist the session
    await service1.create_session(session_id=session_id, user_id=user_id, app_name=app_name, state=initial_state)
    
    # --- Phase 2: Crash & Restart ---
    # Simulate process termination by removing the service instance
    del service1
    
    # Re-instantiate service pointing to the same persistent DB
    service2 = SqliteSessionService(db_path=db_path)
    session2 = await service2.get_session(session_id=session_id, user_id=user_id, app_name=app_name)
    
    assert session2 is not None
    assert session2.id == session_id
    
    # Verify that the 'memory' of processed targets survived the crash
    assert "scanned_targets" in session2.state
    assert "a.py::method_A" in session2.state["processed_targets_list"]
    assert len(session2.state["generated_benchmarks"]) == 1
    
    # --- Phase 3: Resume Generation ---
    # Mock ToolContext with the resumed session
    ctx = MagicMock(spec=ToolContext)
    ctx.session = session2
    
    # Call the Auditor tool logic - it should pick 'method_B'
    result_json = get_prioritized_target(ctx)
    result = json.loads(result_json)
    
    assert result["method_name"] == "method_B"
    assert result["file_path"] == "b.py"
    
    # Verify the progress list was updated in the resumed session
    assert "b.py::method_B" in session2.state["processed_targets_list"]
    
    print("Resumption test passed!")
