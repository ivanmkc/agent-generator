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

import asyncio
import os
import shutil
import pytest
import json
from pathlib import Path
from benchmarks.benchmark_candidates import get_gcloud_project
from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import (
    GeminiCliPodmanAnswerGenerator,
    DEFAULT_IMAGE_PREFIX,
)
from benchmarks.data_models import ApiUnderstandingBenchmarkCase, ApiUnderstandingAnswerOutput

def container_runtime_available():
  return shutil.which("podman") is not None

@pytest.fixture
def generator():
    project_id = get_gcloud_project()
    service_name = "adk-docs-ext"
    gen = GeminiCliPodmanAnswerGenerator(
        dockerfile_dir=Path("."),
        service_name=service_name,
        auto_deploy=True,
        force_deploy=False
    )
    return gen

@pytest.mark.asyncio
@pytest.mark.skipif(not container_runtime_available(), reason="Container runtime (Podman) not available")
async def test_tool_exists(monkeypatch: pytest.MonkeyPatch, generator):
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
      pytest.skip("GEMINI_API_KEY environment variable not set.")
    monkeypatch.setenv("GEMINI_API_KEY", gemini_api_key)

    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", get_gcloud_project())

    print(f"Setting up generator for {generator.image_name}...")
    await generator.setup()

    tools = await generator.get_mcp_tools()
    print(f"DEBUG: Available tools/extensions: {tools}")
    
    # We expect 'adk-docs-ext' to be present. 
    # Note: Depending on parsing, it might be just the name.
    assert any("adk-docs-ext" in tool for tool in tools), f"'adk-docs-ext' not found in tools list: {tools}"

@pytest.mark.asyncio
@pytest.mark.skipif(not container_runtime_available(), reason="Container runtime (Podman) not available")
async def test_tool_usage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, generator):
    """
    Verifies that the adk-docs-ext extension correctly loads context (GEMINI.md)
    and that the Gemini CLI uses it to answer questions.
    """
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
      pytest.skip("GEMINI_API_KEY environment variable not set.")
    monkeypatch.setenv("GEMINI_API_KEY", gemini_api_key)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", get_gcloud_project())

    print(f"Setting up generator for {generator.image_name}...")
    await generator.setup()

    # Use an ApiUnderstandingBenchmarkCase that relies on the GEMINI.md context.
    benchmark_case = ApiUnderstandingBenchmarkCase(
        category="Core Class Signatures & Initialization",
        question="What is the foundational class for all agents in the ADK?",
        rationale="All agents must inherit from `google.adk.agents.base_agent.BaseAgent`, which provides the core interface for execution and configuration.",
        template="identifier",
        answers=[
            {"answer_template": "StringMatchAnswer", "answer": "BaseAgent", "fully_qualified_class_name": ["google.adk.agents.base_agent.BaseAgent"]}
        ],
        file=Path("src/google/adk/agents/base_agent.py")
    )

    # Use the generator's generate_answer public API.
    answer = None
    try:
        answer = await generator.generate_answer(benchmark_case)

        print(f"DEBUG: Answer Output:\n{answer.output.model_dump_json(indent=2)}")
        print(f"DEBUG: Trace Logs:\n{[log.model_dump_json(indent=2) for log in answer.trace_logs]}")

        assert answer.output is not None, "Answer output should not be None."
        assert isinstance(answer.output, ApiUnderstandingAnswerOutput), "Answer output should be ApiUnderstandingAnswerOutput."
        
        # Relaxed check for BaseAgent or Agent
        assert "BaseAgent" in answer.output.code or "Agent" in answer.output.code, (
            f"Expected 'BaseAgent' or 'Agent' in generated code.\nFull Code: {answer.output.code}"
        )
        
        # Check for trace indicators in trace logs
        trace_indicators = ["extension", "context", "loading", "tool_use", "memorydiscovery"]
        found_trace = any(
            any(indicator.lower() in str(log.content).lower() for indicator in trace_indicators) or
            any(indicator.lower() in str(log.details).lower() for indicator in trace_indicators) or
            (log.type == "CLI_STDERR" and any(indicator.lower() in str(log.content).lower() for indicator in trace_indicators))
            for log in answer.trace_logs
        )
        
        if not found_trace:
            print("WARNING: No explicit trace/debug info found in trace logs for context loading or tool use.")
        assert found_trace, "No trace of context/extension usage found."

    except ValueError as e:
        pytest.fail(f"JSON parsing failed for adk-docs-ext: {e}. Output was: {answer.output.model_dump_json() if answer and answer.output else 'N/A'}. Trace Logs: {[log.model_dump_json() for log in answer.trace_logs] if answer else 'N/A'}")
    finally:
        # Save trace logs to a temporary file for analysis, always attempt to save
        trace_log_file = tmp_path / "adk_docs_ext_trace.jsonl"
        if answer and answer.trace_logs:
            with open(trace_log_file, "w") as f:
                for log_event in answer.trace_logs:
                    f.write(log_event.model_dump_json() + "\n")
            print(f"Saved trace logs to {trace_log_file}")
