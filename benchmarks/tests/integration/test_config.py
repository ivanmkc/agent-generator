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

from typing import Dict
from pathlib import Path
from benchmarks.tests.integration.predefined_cases import (
    ADK_BASE_AGENT_QUESTION_CASE_INTERMEDIATE,
    MCP_ADK_RUNNER_CASE,
    STRUCTURED_WORKFLOW_CASE,
)
from benchmarks.tests.integration.config_models import (
    AnyGeneratorConfig,
    PodmanGeneratorConfig,
    CloudRunGeneratorConfig,
    WorkflowAdkGeneratorConfig,
    StructuredWorkflowAdkGeneratorConfig
)

# Map fixture names to their configuration metadata
GENERATOR_METADATA: Dict[str, AnyGeneratorConfig] = {
    "workflow_adk_test_case": WorkflowAdkGeneratorConfig(
        id="workflow_adk_test_case",
        expected_context_files=[], # It clones repo but doesn't use the file-based context check mechanism same way
        expected_tool_uses=[],
        expected_sub_agent_calls=None # No specific sub-agent flow for unstructured workflow
    ),
    "structured_workflow_adk_test_case": StructuredWorkflowAdkGeneratorConfig(
        id="structured_workflow_adk_test_case",
        expected_context_files=[],
        expected_tool_uses=["save_agent_code", "run_current_agent", "write_file"],
        expected_sub_agent_calls=["setup_agent", "knowledge_retrieval_agent", "planner", "verification_creator", "candidate_creator", "verifier", "final_verifier", "teardown_agent"],
        custom_case=STRUCTURED_WORKFLOW_CASE,
    ),
    "podman_base_test_case": PodmanGeneratorConfig(

        id="podman_base_test_case",

        dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/adk-python"),

        expected_context_files=["/workdir/INSTRUCTIONS.md"],

    ),

    "podman_adk_docs_test_case": PodmanGeneratorConfig(

        id="podman_adk_docs_test_case",

        dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/adk-docs-ext"),

        expected_extensions=["adk-docs-ext"],

        expected_mcp_tools=["adk-docs-mcp"],

        custom_case=ADK_BASE_AGENT_QUESTION_CASE_INTERMEDIATE,

        expected_tool_uses=["list_doc_sources", "fetch_docs"],

    ),

    "podman_context7_test_case": PodmanGeneratorConfig(

        id="podman_context7_test_case",

        dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/gemini-cli-mcp-context7"),

        expected_mcp_tools=["context7"],

        custom_case=ADK_BASE_AGENT_QUESTION_CASE_INTERMEDIATE,

    ),

    "podman_mcp_adk_runner_test_case": PodmanGeneratorConfig(

        id="podman_mcp_adk_runner_test_case",

        dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner"),

        expected_mcp_tools=["adk-agent-runner"],

        custom_case=MCP_ADK_RUNNER_CASE,

        expected_tool_uses=["run_adk_agent"],

    ),
    "cloud_run_test_case": CloudRunGeneratorConfig(
        id="cloud_run_test_case",
        dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/base"),
        service_name="gemini-cli-test-service",
    ),
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
