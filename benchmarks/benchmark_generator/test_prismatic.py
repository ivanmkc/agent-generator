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
from benchmarks.benchmark_generator.tools import scan_repository, trace_execution, validate_mutant, save_benchmark_case, get_prioritized_target
from benchmarks.benchmark_generator.agents import create_prismatic_agent, SemaphoreGemini
from benchmarks.api_key_manager import ApiKeyManager

@pytest.fixture
def mock_context():
    """Provides a mocked ToolContext with an initialized Session for tool testing."""
    session = Session(id="test_session", appName="benchmark_test", userId="test_user")
    ctx = MagicMock(spec=ToolContext)
    ctx.session = session
    return ctx

def test_scan_repository(mock_context, tmp_path):
    """Verifies that the Cartographer scan correctly identifies testable methods in a repo."""
    # Create a dummy python file
    p = tmp_path / "my_module.py"
    p.write_text("class Foo:\n  def bar(self):\n    '''Docstring'''\n    x=1\n    y=2\n    return x+y")
    
    result = scan_repository(str(tmp_path), mock_context)
    
    assert "Cartographer scan complete: 1 targets" in result
    targets = mock_context.session.state["scanned_targets"]
    assert len(targets) == 1
    assert targets[0]["method_name"] == "bar"
    assert targets[0]["class_name"] == "Foo"

def test_get_prioritized_target(mock_context):
    """Verifies that the Auditor prioritizes complex methods and handles processed state."""
    targets = [
        {"file_path": "a.py", "method_name": "trivial", "complexity_score": 1, "docstring": None},
        {"file_path": "b.py", "method_name": "complex", "complexity_score": 10, "docstring": "Yes"},
    ]
    mock_context.session.state["scanned_targets"] = targets
    
    # First call - should get 'complex' due to higher complexity and docstring
    res1 = get_prioritized_target(mock_context)
    data1 = json.loads(res1)
    assert data1["method_name"] == "complex"
    assert "b.py::complex" in mock_context.session.state["processed_targets_list"]
    
    # Second call - should get 'trivial'
    res2 = get_prioritized_target(mock_context)
    data2 = json.loads(res2)
    assert data2["method_name"] == "trivial"
    
    # Third call - should return DONE
    res3 = get_prioritized_target(mock_context)
    data3 = json.loads(res3)
    assert data3["status"] == "DONE"

def test_trace_execution(mock_context):
    """Ensures that code execution correctly captures stdout and return values."""
    target = {
        "file_path": "dummy.py",
        "method_name": "test",
        "class_name": None,
        "code_signature": "def test():",
        "docstring": None,
        "complexity_score": 1
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
    snapshot = {
        "stdout": "Hello\n",
        "return_value": "2",
        "valid_usage_code": "print('Hello')",
        "target": {"file_path": "x", "method_name": "x", "code_signature": "x", "complexity_score": 1},
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
    assert agent.name == "PrismaticLoop"

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
    assert agent.name == "PrismaticLoop"

def test_get_prioritized_target_with_coverage(mock_context):
    """Verifies that targets not present in coverage data are prioritized."""
    targets = [
        {"file_path": "covered.py", "method_name": "foo", "complexity_score": 10, "docstring": None},
        {"file_path": "uncovered.py", "method_name": "bar", "complexity_score": 10, "docstring": None},
    ]
    mock_context.session.state["scanned_targets"] = targets
    
    # Inject coverage data: only covered.py is tested
    mock_context.session.state["coverage_data"] = {
        "covered.py": {"summary": {"percent_covered": 100.0}}
    }
    
    # Call Auditor logic
    res = get_prioritized_target(mock_context)
    data = json.loads(res)
    
    # Should pick 'uncovered.py' due to the coverage penalty on 'covered.py'
    assert data["file_path"] == "uncovered.py"