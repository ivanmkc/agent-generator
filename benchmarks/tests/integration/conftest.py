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
Shared fixtures and configuration for integration tests.
"""

import os
import shutil
import pytest
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Any

# --- Generator Imports ---
from benchmarks.answer_generators.base import AnswerGenerator
from benchmarks.answer_generators.gemini_answer_generator import GeminiAnswerGenerator
from benchmarks.answer_generators.gemini_cli_answer_generator import GeminiCliAnswerGenerator
from benchmarks.answer_generators.gemini_cli_local_answer_generator import GeminiCliLocalAnswerGenerator
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import GeminiCliPodmanAnswerGenerator
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import IMAGE_DEFINITIONS

# --- Helper Imports ---
from benchmarks.answer_generators.adk_agents import create_default_adk_agent
from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.tests.integration.predefined_cases import (
    SIMPLE_API_UNDERSTANDING_CASE,
    ADK_BASE_AGENT_QUESTION_CASE_INTERMEDIATE
)

# --- Pre-check Helpers ---
def has_env(var: str) -> bool:
    return bool(os.environ.get(var))

def has_cmd(cmd: str) -> bool:
    return shutil.which(cmd) is not None


# --- Data Models ---

@dataclass
class GeneratorTestCase:
    """Encapsulates a generator instance and its specific test configuration."""
    id: str
    generator: AnswerGenerator
    
    # Simple lists of strings for expected tools
    expected_gemini_cli_extensions: List[str] = field(default_factory=list)
    expected_mcp_tools: List[str] = field(default_factory=list)
    expected_context_files: List[str] = field(default_factory=list)
    
    custom_case: BaseBenchmarkCase = field(default=None)

    trace_indicators: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.custom_case is None:
            from benchmarks.tests.integration.predefined_cases import SIMPLE_API_UNDERSTANDING_CASE
            self.custom_case = SIMPLE_API_UNDERSTANDING_CASE

    @property
    def name(self) -> str:
        return self.id


# --- Shared Configuration Fixtures ---

@pytest.fixture(scope="module")
def model_name() -> str:
    """
    Returns the default model name to use for integration tests.
    This can be overridden or parameterized in specific test modules.
    """
    return "gemini-2.5-flash"


# --- Individual Fixtures returning TestCase objects ---

@pytest.fixture(scope="module")
def api_test_case(model_name: str) -> GeneratorTestCase:
    """Fixture for Direct Gemini API."""
    if not has_env("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    
    gen = GeminiAnswerGenerator(model_name=model_name)
    
    return GeneratorTestCase(
        id="api-direct",
        generator=gen
    )


@pytest.fixture(scope="module")
async def cli_local_test_case(model_name: str) -> GeneratorTestCase:
    """Fixture for Local CLI."""
    if not has_env("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    
    gen = GeminiCliLocalAnswerGenerator(model_name=model_name)
    await gen.setup()
    
    return GeneratorTestCase(
        id="cli-local",
        generator=gen,
        expected_gemini_cli_extensions=[]
    )


@pytest.fixture(scope="module")
def adk_agent_test_case(model_name: str) -> GeneratorTestCase:
    """Fixture for ADK Agents."""
    if not has_env("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    agent = create_default_adk_agent(model_name=model_name)
    gen = AdkAnswerGenerator(agent=agent)
    
    return GeneratorTestCase(
        id="adk-agent",
        generator=gen
    )


@pytest.fixture(scope="module")
async def podman_base_test_case(model_name: str) -> GeneratorTestCase:
    """Fixture for Podman Base Image."""
    
    # Check for Proxy Mode
    if os.environ.get("TEST_GENERATOR_ID") == "podman_base_test_case" and os.environ.get("TEST_GENERATOR_URL"):
        print(f"[Fixture] Using Proxy Generator for podman_base_test_case at {os.environ['TEST_GENERATOR_URL']}")
        gen = GeminiCliPodmanAnswerGenerator(
            dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/adk-python"),
            image_name="gemini-cli:adk-python",
            image_definitions=IMAGE_DEFINITIONS,
            model_name=model_name,
            service_url=os.environ["TEST_GENERATOR_URL"]
        )
        await gen.setup()
    else:
        # Check for parallel execution without orchestrator
        if os.environ.get("PYTEST_XDIST_WORKER") and not os.environ.get("TEST_GENERATOR_URL"):
            pytest.skip("Skipping resource-heavy Podman test in parallel mode without orchestrator. Use 'python benchmarks/tests/integration/test_unified_generators.py' for optimized execution.")

        if not has_cmd("podman"):
            pytest.skip("Podman not installed")

        gen = GeminiCliPodmanAnswerGenerator(
            dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/adk-python"),
            image_name="gemini-cli:adk-python",
            image_definitions=IMAGE_DEFINITIONS,
            model_name=model_name
        )
        print(f"--- [Setup] Initializing {gen.image_name} ---")
        await gen.setup()
    
    return GeneratorTestCase(
        id="podman-base",
        generator=gen,
        expected_gemini_cli_extensions=[],
        expected_context_files=["/workdir/INSTRUCTIONS.md"]
    )


@pytest.fixture(scope="module")
async def podman_adk_docs_test_case(model_name: str) -> GeneratorTestCase:
    """Fixture for Podman ADK Docs Extension (MCP)."""

    # Check for Proxy Mode
    if os.environ.get("TEST_GENERATOR_ID") == "podman_adk_docs_test_case" and os.environ.get("TEST_GENERATOR_URL"):
        print(f"[Fixture] Using Proxy Generator for podman_adk_docs_test_case at {os.environ['TEST_GENERATOR_URL']}")
        gen = GeminiCliPodmanAnswerGenerator(
            dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/adk-docs-ext"),
            image_name="gemini-cli:adk-docs-ext",
            image_definitions=IMAGE_DEFINITIONS,
            model_name=model_name,
            service_url=os.environ["TEST_GENERATOR_URL"]
        )
        await gen.setup()
    else:
        # Check for parallel execution without orchestrator
        if os.environ.get("PYTEST_XDIST_WORKER") and not os.environ.get("TEST_GENERATOR_URL"):
            pytest.skip("Skipping resource-heavy Podman test in parallel mode without orchestrator. Use 'python benchmarks/tests/integration/test_unified_generators.py' for optimized execution.")

        if not has_cmd("podman"):
            pytest.skip("Podman not installed")

        gen = GeminiCliPodmanAnswerGenerator(
            dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/adk-docs-ext"),
            image_name="gemini-cli:adk-docs-ext",
            image_definitions=IMAGE_DEFINITIONS,
            model_name=model_name
        )
        print(f"--- [Setup] Initializing {gen.image_name} ---")
        await gen.setup()
    
    # Specific case for this tool
    case = ADK_BASE_AGENT_QUESTION_CASE_INTERMEDIATE
    
    # Traces relevant to this specific case and tool combination
    traces = ["extension", "context", "loading"]

    return GeneratorTestCase(
        id="podman-adk-docs",
        generator=gen,
        expected_gemini_cli_extensions=[],
        expected_mcp_tools=["adk-docs-mcp"],
        custom_case=case,
        trace_indicators=traces
    )


@pytest.fixture(scope="module")
async def podman_context7_test_case(model_name: str) -> GeneratorTestCase:
    """Fixture for Podman ADK Docs Extension (MCP)."""

    # Check for Proxy Mode
    if os.environ.get("TEST_GENERATOR_ID") == "podman_context7_test_case" and os.environ.get("TEST_GENERATOR_URL"):
        print(f"[Fixture] Using Proxy Generator for podman_context7_test_case at {os.environ['TEST_GENERATOR_URL']}")
        gen = GeminiCliPodmanAnswerGenerator(
            dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/gemini-cli-mcp-context7"),
            image_name="gemini-cli:mcp-context7",
            image_definitions=IMAGE_DEFINITIONS,
            model_name=model_name,
            service_url=os.environ["TEST_GENERATOR_URL"]
        )
        await gen.setup()
    else:
        # Check for parallel execution without orchestrator
        if os.environ.get("PYTEST_XDIST_WORKER") and not os.environ.get("TEST_GENERATOR_URL"):
            pytest.skip("Skipping resource-heavy Podman test in parallel mode without orchestrator. Use 'python benchmarks/tests/integration/test_unified_generators.py' for optimized execution.")

        if not has_cmd("podman"):
            pytest.skip("Podman not installed")

        gen = GeminiCliPodmanAnswerGenerator(
            dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/gemini-cli-mcp-context7"),
            image_name="gemini-cli:mcp-context7",
            image_definitions=IMAGE_DEFINITIONS,
            model_name=model_name
        )
        print(f"--- [Setup] Initializing {gen.image_name} ---")
        await gen.setup()
    
    # Specific case for this tool
    case = ADK_BASE_AGENT_QUESTION_CASE_INTERMEDIATE
    
    # Traces relevant to this specific case and tool combination
    traces = ["extension", "context", "loading"]

    return GeneratorTestCase(
        id="podman-mcp-context7",
        generator=gen,
        expected_gemini_cli_extensions=[],
        expected_mcp_tools=[],
        custom_case=case,
        trace_indicators=traces
    )

@pytest.fixture(scope="module")
async def cloud_run_test_case(model_name: str) -> GeneratorTestCase:
    """Fixture for Cloud Run deployed Gemini CLI."""
    if not has_env("GOOGLE_CLOUD_PROJECT"):
        pytest.skip("GOOGLE_CLOUD_PROJECT not set for Cloud Run tests")
    
    # Import here to avoid circular dependencies and only if needed
    from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_cloud_run_answer_generator import GeminiCliCloudRunAnswerGenerator

    # Check for Proxy Mode
    if os.environ.get("TEST_GENERATOR_ID") == "cloud_run_test_case" and os.environ.get("TEST_GENERATOR_URL"):
        print(f"[Fixture] Using Proxy Generator for cloud_run_test_case at {os.environ['TEST_GENERATOR_URL']}")
        gen = GeminiCliCloudRunAnswerGenerator(
            dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/base"),
            service_name="gemini-cli-test-service",
            model_name=model_name,
            service_url=os.environ["TEST_GENERATOR_URL"]
        )
        # In proxy mode, we still call setup() to resolve auth if needed, but it skips deployment
        await gen.setup()
    else:
        # Use a generic base image for the CLI server
        gen = GeminiCliCloudRunAnswerGenerator(
            dockerfile_dir=Path("benchmarks/answer_generators/gemini_cli_docker/base"),
            service_name="gemini-cli-test-service", # Unique service name for testing
            model_name=model_name,
            # It's good practice to set a specific region for Cloud Run deployments in tests
            region="us-central1" 
        )

        print(f"--- [Setup] Initializing {gen.service_name} (Cloud Run) ---")
        await gen.setup()

    return GeneratorTestCase(
        id="cloud-run-base",
        generator=gen,
        expected_gemini_cli_extensions=[], # No specific extensions for the base image
        expected_mcp_tools=[] # No MCP tools for the base image
    )


@pytest.fixture(scope="module")
async def cli_fix_error_test_case(model_name: str, tmp_path_factory: pytest.TempPathFactory) -> GeneratorTestCase:
    """Fixture for Local CLI running a Fix Error case."""
    if not has_env("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    
    gen = GeminiCliLocalAnswerGenerator(model_name=model_name)
    await gen.setup()
    
    # Create a temporary directory for this specific test case setup
    case_tmp_path = tmp_path_factory.mktemp("fix_error_case")
    
    # Setup files for the fix error case
    test_file_path = case_tmp_path / "test_agent.py"
    unfixed_file_path = case_tmp_path / "unfixed.py"
    fixed_file_path = case_tmp_path / "fixed.py"

    test_file_path.write_text("def test_fixed(): pass")
    unfixed_file_path.write_text("def unfixed(): pass")
    fixed_file_path.write_text("def fixed(): pass")

    from benchmarks.tests.integration.test_utils import create_fix_error_benchmark_case
    case = create_fix_error_benchmark_case(
        case_path=case_tmp_path,
        name="Test Fix Error",
        description="Fix a bug by creating a valid agent.",
        requirements=[
            (
                "The solution MUST import `BaseAgent` directly from"
                " `google.adk.agents`."
            ),
            (
                "The `create_agent` function MUST have the return type annotation"
                " `-> BaseAgent`."
            ),
        ],
    )

    return GeneratorTestCase(
        id="cli-fix-error",
        generator=gen,
        expected_gemini_cli_extensions=[],
        custom_case=case
    )


# --- Meta-Fixture ---

TEST_CASE_FIXTURES = [
    "api_test_case",
    "cli_local_test_case",
    "adk_agent_test_case",
    "podman_base_test_case",
    "podman_adk_docs_test_case",
    "podman_context7_test_case",
    "cloud_run_test_case",
    "cli_fix_error_test_case", # Add the new Fix Error test case
]

@pytest.fixture(params=TEST_CASE_FIXTURES, scope="module")
def test_case(request: pytest.FixtureRequest) -> GeneratorTestCase:
    """
    Meta-fixture that iterates over all registered TestCase fixtures.
    """
    return request.getfixturevalue(request.param)