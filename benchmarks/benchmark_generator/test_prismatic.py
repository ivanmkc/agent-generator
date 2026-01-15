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
Unit tests for the Prismatic Generator's core components.

This suite verifies the individual tool functions (Scanning, Tracing, Sandboxing)
and ensures that the multi-agent orchestration can be correctly instantiated
with and without specialized API key management.
"""

import pytest
import json
import asyncio
from unittest.mock import MagicMock
from google.adk.tools import ToolContext
from google.adk.sessions import Session
from benchmarks.benchmark_generator.tools import (
    scan_repository, trace_execution, validate_mutant, 
    save_benchmark_case, list_prioritized_targets, select_target
)
from benchmarks.benchmark_generator.agents import create_prismatic_agent, SemaphoreGemini
from benchmarks.api_key_manager import ApiKeyManager
from benchmarks.benchmark_generator.models import TargetType

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
    p.write_text("class Foo:\n  def bar(self):\n    '''Docstring'''\n    x=1\n    y=2\n    return x+y")
    
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
    bar_target = next((t for t in targets if t["name"] == "bar" and t["type"] == "method"), None)
    assert bar_target is not None
    assert bar_target["id"] == "my_module.Foo.bar"
    
    # Verify usage was counted
    assert bar_target["usage_score"] >= 1

def test_list_prioritized_targets(mock_context):
    """Verifies that the Auditor prioritizes based on Coverage Lift and Usage."""
    targets = [
        {
            "id": "unused.unused", "type": "method", "name": "unused", 
            "file_path": "unused.py", "complexity_score": 50.0, "docstring": "Yes", "usage_score": 0
        },
        {
            "id": "popular.popular", "type": "method", "name": "popular", 
            "file_path": "popular.py", "complexity_score": 5.0, "docstring": "Yes", "usage_score": 10
        },
    ]
    mock_context.session.state["scanned_targets"] = targets
    
    # First call:
    # 'unused': Usage(0) + Lift(50 * 1.0 * 20 = 1000) = 1000
    # 'popular': Usage(100) + Lift(5 * 1.0 * 20 = 100) = 200
    # So 'unused' should be first.
    
    res_list_json = list_prioritized_targets(mock_context, limit=2)
    res_list = json.loads(res_list_json)
    assert res_list[0]["id"] == "unused.unused"
    
    # Simulate processing 'unused'
    res_select = select_target("unused.unused", mock_context)
    data_select = json.loads(res_select)
    assert data_select["id"] == "unused.unused"
    
    # Verify state update
    processed_list = mock_context.session.state["processed_targets_list"]
    assert "unused.unused" in processed_list
    
    # Second call - should get 'popular'
    res_list_2 = list_prioritized_targets(mock_context, limit=1)
    res_list_data_2 = json.loads(res_list_2)
    assert res_list_data_2[0]["id"] == "popular.popular"
    
    # Process popular
    select_target("popular.popular", mock_context)
    
    # Third call - should return DONE
    res_done = list_prioritized_targets(mock_context)
    assert res_done == "DONE"

def test_trace_execution(mock_context):
    """Ensures that code execution correctly captures stdout and return values."""
    target = {
        "id": "dummy.test",
        "type": "method",
        "name": "test",
        "file_path": "dummy.py",
        "complexity_score": 1.0,
        "usage_score": 0
    }
    code = "result = 1 + 1\nprint('Hello')"
    
    result = trace_execution(code, target, mock_context)
    data = json.loads(result)
    
    assert data["status"] == "success"
    snapshot = mock_context.session.state["current_snapshot"]
    assert snapshot["return_value"] == "2"
    assert "Hello" in snapshot["stdout"]

def test_validate_mutant(mock_context):
    """Verifies that the Sandbox correctly identifies valid (divergent) distractors."""
    # Setup snapshot
    target = {
        "id": "dummy.test",
        "type": "method",
        "name": "test",
        "file_path": "dummy.py",
        "complexity_score": 1.0,
        "usage_score": 0
    }
    snapshot = {
        "stdout": "Hello\n",
        "return_value": "'N/A'",
        "valid_usage_code": "print('Hello')",
        "target": target,
        "local_vars": {},
        "execution_time": 0.1
    }
    mock_context.session.state["current_snapshot"] = snapshot
    
    # 1. Equivalent Mutant - Should fail validation
    res1 = validate_mutant("print('Hello')", mock_context)
    assert json.loads(res1)["valid"] is False
    
    # 2. Divergent Mutant - Should pass validation
    res2 = validate_mutant("print('World')", mock_context)
    assert json.loads(res2)["valid"] is True
    
    # 3. Crash Mutant - Should pass validation (it is a valid fail)
    res3 = validate_mutant("raise ValueError('Oops')", mock_context)
    assert json.loads(res3)["valid"] is True

def test_save_benchmark_case(mock_context):
    """Verifies that generated benchmarks are correctly persisted to the session state."""
    case = {"question": "Q", "options": {"A": "1"}, "correct_answer": "A", "benchmark_type": "multiple_choice"}
    res = save_benchmark_case(json.dumps(case), mock_context)
    
    assert "Benchmark saved" in res
    assert "Stats:" in res
    assert len(mock_context.session.state["generated_benchmarks"]) == 1
    assert mock_context.session.state["generated_benchmarks"][0]["question"] == "Q"

def test_agent_creation():
    """Sanity check that the Prismatic loop agent can be instantiated."""
    agent = create_prismatic_agent()
    # Updated name expectation from agents.py
    assert agent.name == "PrismaticRunner"

def test_semaphore_gemini_instantiation():
    """Verifies that the SemaphoreGemini class correctly stores the semaphore."""
    sem = asyncio.Semaphore(1)
    akm = MagicMock(spec=ApiKeyManager)
    model = SemaphoreGemini(semaphore=sem, api_key_manager=akm, model="test")
    assert model._semaphore == sem

def test_prismatic_agent_creation_with_manager():
    """Ensures the orchestrator correctly integrates with the ApiKeyManager."""
    akm = MagicMock(spec=ApiKeyManager)
    agent = create_prismatic_agent(api_key_manager=akm, concurrency=5)
    assert agent.name == "PrismaticRunner"

def test_list_prioritized_targets_with_coverage(mock_context):
    """Verifies that targets not present in coverage data are prioritized."""
    targets = [
        {
            "id": "covered.foo", "type": "method", "name": "foo",
            "file_path": "covered.py", "complexity_score": 10.0, "docstring": None, "usage_score": 0
        },
        {
            "id": "uncovered.bar", "type": "method", "name": "bar",
            "file_path": "uncovered.py", "complexity_score": 10.0, "docstring": None, "usage_score": 0
        },
    ]
    mock_context.session.state["scanned_targets"] = targets
    
    # Inject coverage data: only covered.py is tested
    mock_context.session.state["coverage_data"] = {
        "covered.py": {"summary": {"percent_covered": 100.0}}
    }
    
    # Call Auditor logic
    res_json = list_prioritized_targets(mock_context)
    data = json.loads(res_json)
    
    # Should pick 'uncovered.bar' (Lift = 10 * 1.0 * 20 = 200) vs 'covered.foo' (Lift = 10 * 0.1 * 20 = 20)
    assert data[0]["id"] == "uncovered.bar"