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
Shared configuration for integration tests.
Defines the metadata for each generator test case to allow dynamic orchestration.
"""

from typing import Dict, Any
from benchmarks.tests.integration.predefined_cases import (
    ADK_BASE_AGENT_QUESTION_CASE_INTERMEDIATE,
    FIX_ERROR_MINIMAL_AGENT_CONTENT,
    MCP_ADK_RUNNER_CASE,
)
from benchmarks.data_models import FixErrorBenchmarkCase

# Map fixture names to their configuration metadata
GENERATOR_METADATA: Dict[str, Dict[str, Any]] = {
    "podman_base_test_case": {
        "id": "podman_base_test_case",
        "type": "podman",
        "dockerfile_dir": "benchmarks/answer_generators/gemini_cli_docker/adk-python",
        "image_name": "gemini-cli:adk-python",
        "expected_context_files": ["/workdir/INSTRUCTIONS.md"],
        "expected_extensions": [],
        "expected_mcp_tools": [],
        "custom_case": None, # Defaults to standard API check
        "expected_tool_uses": []
    },
    "podman_adk_docs_test_case": {
        "id": "podman_adk_docs_test_case",
        "type": "podman",
        "dockerfile_dir": "benchmarks/answer_generators/gemini_cli_docker/adk-docs-ext",
        "image_name": "gemini-cli:adk-docs-ext",
        "expected_context_files": [],
        "expected_extensions": ["adk-docs-ext"],
        "expected_mcp_tools": ["adk-docs-mcp"],
        "custom_case": ADK_BASE_AGENT_QUESTION_CASE_INTERMEDIATE,
        "expected_tool_uses": ["list_doc_sources", "fetch_docs",]
    },
    "podman_context7_test_case": {
        "id": "podman_context7_test_case",
        "type": "podman",
        "dockerfile_dir": "benchmarks/answer_generators/gemini_cli_docker/gemini-cli-mcp-context7",
        "image_name": "gemini-cli:mcp-context7",
        "expected_context_files": ["/workdir/INSTRUCTIONS.md"],
        "expected_extensions": [],
        "expected_mcp_tools": ["context7"],
        "custom_case": ADK_BASE_AGENT_QUESTION_CASE_INTERMEDIATE,
        "expected_tool_uses": []
    },
    "podman_mcp_adk_runner_test_case": {
        "id": "podman_mcp_adk_runner_test_case",
        "type": "podman",
        "dockerfile_dir": "benchmarks/answer_generators/gemini_cli_docker/mcp-adk-agent-runner",
        "image_name": "gemini-cli:mcp-adk-agent-runner",
        "expected_context_files": [],
        "expected_extensions": [],
        "expected_mcp_tools": ["adk-agent-runner"],
        "custom_case": MCP_ADK_RUNNER_CASE,
        "expected_tool_uses": ["run_adk_agent"]
    },
    "cloud_run_test_case": {
        "id": "cloud_run_test_case",
        "type": "cloud_run",
        "dockerfile_dir": "benchmarks/answer_generators/gemini_cli_docker/base",
        "service_name": "gemini-cli-test-service",
        "region": "us-central1",
        "expected_context_files": [],
        "expected_extensions": [],
        "expected_mcp_tools": [],
        "custom_case": None,
        "expected_tool_uses": []
    }
}

# List of unmanaged (local) fixtures
# These are still defined manually in conftest.py because they don't involve the orchestration loop
LOCAL_FIXTURES = [
    "api_test_case",
    "cli_local_test_case",
    "adk_agent_test_case",
    "cli_fix_error_test_case", 
]

# The complete list of test cases is now the local ones + the keys of the managed ones
# This flat list allows the 'test_case' fixture to iterate over everything directly
TEST_CASE_FIXTURES = LOCAL_FIXTURES + list(GENERATOR_METADATA.keys())