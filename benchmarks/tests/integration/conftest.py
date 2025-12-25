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
from benchmarks.answer_generators.gemini_cli_answer_generator import (
    GeminiCliAnswerGenerator,
)
from benchmarks.answer_generators.gemini_cli_local_answer_generator import (
    GeminiCliLocalAnswerGenerator,
)
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import (
    GeminiCliPodmanAnswerGenerator,
)
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import (
    IMAGE_DEFINITIONS,
)

# --- Helper Imports ---
from benchmarks.answer_generators.adk_agents import create_default_adk_agent
from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.tests.integration.predefined_cases import (
    SIMPLE_API_UNDERSTANDING_CASE,
    ADK_BASE_AGENT_QUESTION_CASE_INTERMEDIATE,
)


# --- Pre-check Helpers ---
def has_env(var: str) -> bool:
    return bool(os.environ.get(var))


def has_cmd(cmd: str) -> bool:
    return shutil.which(cmd) is not None


# --- Data Models ---


@dataclass
class GeneratorTestCase:
    """
    Encapsulates a generator instance and its specific test configuration.

    Attributes:
        id: A unique identifier for this test case instance.
        generator: An instance of `AnswerGenerator` to be tested.
        expected_gemini_cli_extensions: A list of expected Gemini CLI extension IDs
                                        that the generator should discover.
        expected_mcp_tools: A list of expected MCP tool names that the generator
                            should discover.
        expected_context_files: A list of expected context file paths that the generator
                                should load (for memory context tests).
        custom_case: An optional `BaseBenchmarkCase` instance to be used instead
                     of the default `SIMPLE_API_UNDERSTANDING_CASE`.
        expected_tool_uses: A list of tool names or log indicators expected to be found
                          within the trace logs of a successful generation.
    """

    id: str
    generator: AnswerGenerator

    # Simple lists of strings for expected tools
    expected_gemini_cli_extensions: List[str] = field(default_factory=list)
    expected_mcp_tools: List[str] = field(default_factory=list)
    expected_context_files: List[str] = field(default_factory=list)

    custom_case: BaseBenchmarkCase = field(default=None)

    expected_tool_uses: List[str] = field(default_factory=list)
    expected_sub_agent_calls: Optional[List[str]] = field(default=None)

    def __post_init__(self):
        if self.custom_case is None:
            from benchmarks.tests.integration.predefined_cases import (
                SIMPLE_API_UNDERSTANDING_CASE,
            )

            self.custom_case = SIMPLE_API_UNDERSTANDING_CASE

    @property
    def name(self) -> str:
        return self.id


# --- Shared Configuration Fixtures ---

from benchmarks.tests.integration.test_config import GENERATOR_METADATA


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

    return GeneratorTestCase(id="api-direct", generator=gen)


@pytest.fixture(scope="module")
async def cli_local_test_case(model_name: str) -> GeneratorTestCase:
    """Fixture for Local CLI."""
    if not has_env("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    gen = GeminiCliLocalAnswerGenerator(model_name=model_name)
    await gen.setup()

    return GeneratorTestCase(
        id="cli-local", generator=gen, expected_gemini_cli_extensions=[]
    )


@pytest.fixture(scope="module")
def adk_agent_test_case(model_name: str) -> GeneratorTestCase:
    """Fixture for ADK Agents."""
    if not has_env("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    agent = create_default_adk_agent(model_name=model_name)
    gen = AdkAnswerGenerator(agent=agent)

    return GeneratorTestCase(id="adk-agent", generator=gen)


@pytest.fixture(scope="module")
async def managed_generator_test_case(
    request: pytest.FixtureRequest, model_name: str
) -> GeneratorTestCase:
    """
    Generic fixture for all managed generators (Podman/Cloud Run).
    It expects the request.param to be the configuration ID string.
    """
    # The param is passed from the meta-fixture 'test_case' which iterates over TEST_CASE_FIXTURES.
    # However, 'managed_generator_test_case' itself is not parameterized by pytest directly here
    # because it is called via `request.getfixturevalue` in `test_case`.
    # BUT, `test_case` passes the fixture NAME string (e.g. "managed_generator_test_case[podman_base]").
    # Wait, the meta-fixture logic in `test_case` expects the param to be a fixture NAME.
    # To support dynamic orchestration, we need `test_case` to handle this.

    # Actually, simpler: We make `managed_generator_test_case` parameterized itself
    # over the keys of GENERATOR_METADATA.
    pass


# We need to restructure slightly.
# OLD: test_case iterates over ["api_test_case", "podman_base_test_case", ...]
# NEW: test_case iterates over ["api_test_case", ..., "managed_generator_test_case"]
# AND managed_generator_test_case is parameterized by the config keys.

from benchmarks.tests.integration.config_models import (
    PodmanGeneratorConfig,
    CloudRunGeneratorConfig,
)


@pytest.fixture(params=list(GENERATOR_METADATA.keys()), scope="module")
async def managed_generator_test_case(
    request: pytest.FixtureRequest, model_name: str
) -> GeneratorTestCase:
    """
    Generic fixture for all managed generators defined in GENERATOR_METADATA.
    """
    config_id = request.param
    config = GENERATOR_METADATA[config_id]

    gen_type = config.type

    service_url = None
    # Check for Proxy Mode: The orchestrator sets TEST_GENERATOR_ID to the specific config ID
    if os.environ.get("TEST_GENERATOR_ID") == config_id and os.environ.get(
        "TEST_GENERATOR_URL"
    ):
        print(
            f"[Fixture] Using Proxy Generator for {config_id} at {os.environ['TEST_GENERATOR_URL']}"
        )
        service_url = os.environ["TEST_GENERATOR_URL"]
    else:
        # Check for parallel execution without orchestrator
        if os.environ.get("PYTEST_XDIST_WORKER") and not os.environ.get(
            "TEST_GENERATOR_URL"
        ):
            pytest.skip(
                f"Skipping resource-heavy {gen_type} test {config_id} in parallel mode without orchestrator."
            )

        if gen_type == "podman" and not has_cmd("podman"):
            pytest.skip("Podman not installed")
        if gen_type == "cloud_run" and not has_env("GOOGLE_CLOUD_PROJECT"):
            pytest.skip("GOOGLE_CLOUD_PROJECT not set")

    # Instantiate the correct generator class
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", None)
    gen = config.create_generator(model_name=model_name, project_id=project_id)

    print(f"--- [Setup] Initializing {gen.name} ---")
    await gen.setup()

    return GeneratorTestCase(
        id=config.id,
        generator=gen,
        expected_gemini_cli_extensions=config.expected_extensions,
        expected_mcp_tools=config.expected_mcp_tools,
        expected_context_files=config.expected_context_files,
        custom_case=config.custom_case,
        expected_tool_uses=config.expected_tool_uses,
        expected_sub_agent_calls=config.expected_sub_agent_calls,
    )


@pytest.fixture(scope="module")
async def cli_fix_error_test_case(
    model_name: str, tmp_path_factory: pytest.TempPathFactory
) -> GeneratorTestCase:
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
        custom_case=case,
    )


# --- Meta-Fixture ---

from benchmarks.tests.integration.test_config import TEST_CASE_FIXTURES


@pytest.fixture(params=TEST_CASE_FIXTURES, scope="module")
async def test_case(
    request: pytest.FixtureRequest, model_name: str
) -> GeneratorTestCase:
    """
    Meta-fixture that provides the GeneratorTestCase for the current test iteration.
    It handles both:
    1. Managed generators (defined in test_config.py): Instantiates them dynamically.
    2. Local fixtures (defined in conftest.py): Resolves them via getfixturevalue.
    """
    case_id = request.param

    # 1. Check if it's a managed generator
    if case_id in GENERATOR_METADATA:
        config = GENERATOR_METADATA[case_id]
        gen_type = config.type

        service_url = None
        # Check for Proxy Mode
        if os.environ.get("TEST_GENERATOR_ID") == case_id and os.environ.get(
            "TEST_GENERATOR_URL"
        ):
            print(
                f"[Fixture] Using Proxy Generator for {case_id} at {os.environ['TEST_GENERATOR_URL']}"
            )
            service_url = os.environ["TEST_GENERATOR_URL"]
        else:
            # Check for parallel execution without orchestrator
            if os.environ.get("PYTEST_XDIST_WORKER") and not os.environ.get(
                "TEST_GENERATOR_URL"
            ):
                pytest.skip(
                    f"Skipping resource-heavy {gen_type} test {case_id} in parallel mode without orchestrator."
                )

            if gen_type == "podman" and not has_cmd("podman"):
                pytest.skip("Podman not installed")
            if gen_type == "cloud_run" and not has_env("GOOGLE_CLOUD_PROJECT"):
                pytest.skip("GOOGLE_CLOUD_PROJECT not set")

        # Instantiate generator
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", None)
        gen = config.create_generator(model_name=model_name, project_id=project_id)

        custom_case_data = config.custom_case
        custom_case_instance = custom_case_data  # It's already an instance or None

        print(f"--- [Setup] Initializing {gen.name} ---")
        await gen.setup()
        
        return GeneratorTestCase(
            id=config.id,
            generator=gen,
            expected_gemini_cli_extensions=config.expected_extensions,
            expected_mcp_tools=config.expected_mcp_tools,
            expected_context_files=config.expected_context_files,
            custom_case=custom_case_instance,
            expected_tool_uses=config.expected_tool_uses,
            expected_sub_agent_calls=config.expected_sub_agent_calls,
        )

    # 2. Fallback to Local Fixtures
    else:
        # For async fixtures, getfixturevalue returns the result directly (awaited by pytest)
        # But wait, request.getfixturevalue() is synchronous-ish in how it resolves?
        # If the target fixture is async, getfixturevalue returns the value (not coroutine)
        # because Pytest handles the loop.
        return request.getfixturevalue(case_id)
