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
Verification script for configure_adk_features_mc/benchmark.yaml.
This script verifies that the API surface, classes, and signatures assumed by the
benchmark questions actually exist and behave as expected in the codebase.
"""

import ast
import importlib
import inspect
from pathlib import Path
import sys

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.run_config import RunConfig
from google.adk.apps import App
from google.adk.artifacts.base_artifact_service import BaseArtifactService
from google.adk.auth.credential_manager import CredentialManager
from google.adk.cli.cli_tools_click import cli_api_server
from google.adk.cli.cli_tools_click import cli_deploy_cloud_run
from google.adk.evaluation.eval_case import EvalCase
from google.adk.evaluation.eval_case import IntermediateData
from google.adk.events.event import Event
from google.adk.plugins.context_filter_plugin import ContextFilterPlugin
from google.adk.plugins.global_instruction_plugin import GlobalInstructionPlugin
from google.adk.plugins.reflect_retry_tool_plugin import ReflectAndRetryToolPlugin
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.genai import types
import pytest


# --- Question 1: Import Runner ---
def test_q1_runner_import():
    """Question 1: Correct import statement for Runner."""
    # Correct Option B
    assert Runner.__module__ == "google.adk.runners"

    # Distractor A: google.adk.factory (Invalid)
    try:
        import google.adk.factory

        pytest.fail("google.adk.factory should not exist")
    except ImportError:
        pass

    # Distractor C: google.adk.core (Invalid)
    try:
        import google.adk.core

        assert not hasattr(google.adk.core, "Runner")
    except ImportError:
        pass


# --- Question 2: Import Event ---
def test_q2_event_import():
    """Question 2: Correct import for Event class."""
    # Correct Option (implied via NOTA or corrected question): google.adk.events.event
    assert Event.__module__ == "google.adk.events.event"


# --- Question 3: runner.run_async params ---
def test_q3_run_async_params():
    """Question 3: Parameter for user input in run_async."""
    sig = inspect.signature(Runner.run_async)
    assert "new_message" in sig.parameters
    assert "message" not in sig.parameters
    assert "content" not in sig.parameters


# --- Question 4: App initialization ---
def test_q4_app_init():
    """Question 4: App parameters and validation."""
    # Verify 'name' exists (via Pydantic fields)
    assert "name" in App.model_fields

    # Verify Runner takes 'app' or 'app_name'
    sig_runner = inspect.signature(Runner.__init__)
    assert "app" in sig_runner.parameters
    assert "app_name" in sig_runner.parameters

    # Negative Test (Distractor B): App(application=...)
    from pydantic import ValidationError

    try:
        dummy_agent = BaseAgent(name="dummy", sub_agents=[])
        App(name="test", root_agent=dummy_agent, application="something")
        pytest.fail("App(application=...) should have failed")
    except ValidationError as e:
        assert "application" in str(e) or "Extra inputs" in str(e)


# --- Question 5: GenAI content unit ---
def test_q5_genai_content_part():
    """Question 5: Fundamental unit of content."""
    # Just checking existence of types.Part
    assert types.Part


# --- Question 6: User message construction ---
def test_q6_user_message():
    """Question 6: Constructing user message."""
    # types.Content takes parts
    sig = inspect.signature(types.Content)
    assert "parts" in sig.parameters or "parts" in types.Content.model_fields


# --- Question 7: Custom Agent Base Class ---
def test_q7_base_agent_abc():
    """Question 7: Base class for custom agents."""
    assert issubclass(BaseAgent, object)
    assert hasattr(BaseAgent, "run_async")


# --- Question 8: Custom Tool Implementation ---
def test_q8_base_tool_abc():
    """Question 8: BaseTool implementation."""
    from abc import ABC

    assert issubclass(BaseTool, ABC)
    assert hasattr(BaseTool, "run_async")


# --- Question 9: before_tool_callback signature ---
# (Implicitly verified by usage in codebase, hard to verify exact signature enforcement dynamically without deeper inspection)

# --- Question 10: run_on_event_callback signature ---
# (Same as above)


# --- Question 11: InvocationContext purpose ---
def test_q11_invocation_context():
    """Question 11: InvocationContext structure."""
    type_hints = inspect.get_annotations(InvocationContext)
    assert "session" in type_hints
    assert "agent_states" in type_hints
    assert "session_service" in type_hints


# --- Question 12: Artifact Service ---
def test_q12_artifact_service_abc():
    """Question 12: BaseArtifactService."""
    assert inspect.isabstract(BaseArtifactService)


# --- Question 13: Event Compaction Config ---
# (Verified by existence of EventsCompactionConfig in App - see test_q4 implicitly or explicitly here)
def test_q13_compaction_config():
    assert "events_compaction_config" in App.model_fields


# --- Question 14: InMemory Persistence ---
def test_q14_in_memory_persistence():
    """Question 14: InMemorySessionService storage."""
    service = InMemorySessionService()
    assert isinstance(service.sessions, dict)


# --- Question 15: state_delta ---
# (Hard to verify without running, but checking if run_async accepts it)
def test_q15_state_delta_param():
    """Question 15: state_delta in run_async."""
    sig = inspect.signature(Runner.run_async)
    assert "state_delta" in sig.parameters


# --- Questions 16-24: Various API checks ---
# Skipped explicit tests for some purely conceptual ones, but covering key classes.


# --- Question 25: LoopAgent parameters ---
def test_q25_loop_agent_params():
    """Question 25: LoopAgent max_iterations."""
    assert "max_iterations" in LoopAgent.model_fields


# --- Question 26: RunConfig limits ---
def test_q26_run_config_limits():
    """Question 26: RunConfig max_llm_calls."""
    config = RunConfig()
    assert hasattr(config, "max_llm_calls")
    assert config.max_llm_calls == 500
    # Negative: llm_call_limit
    assert not hasattr(config, "llm_call_limit")


# --- Question 27: Save Artifacts Plugin ---
def test_q27_save_files_plugin():
    """Question 27: SaveFilesAsArtifactsPlugin."""
    assert SaveFilesAsArtifactsPlugin


# --- Question 28: Response Modality ---
def test_q28_response_modality():
    """Question 28: RunConfig response_modalities."""
    config = RunConfig()
    assert hasattr(config, "response_modalities")


# --- Question 29: Global Instruction ---
def test_q29_global_instruction():
    """Question 29: GlobalInstructionPlugin."""
    assert GlobalInstructionPlugin


# --- Question 30: Retry Plugin ---
def test_q30_retry_plugin():
    """Question 30: ReflectAndRetryToolPlugin."""
    assert ReflectAndRetryToolPlugin
    # Negative: ReflectRetryToolPlugin (incorrect name check)
    try:
        from google.adk.plugins.reflect_retry_tool_plugin import ReflectRetryToolPlugin

        pytest.fail(
            "ReflectRetryToolPlugin should not exist (or is not the correct answer)"
        )
    except ImportError:
        pass


# --- Question 31: Context Filter ---
def test_q31_context_filter():
    """Question 31: ContextFilterPlugin."""
    assert ContextFilterPlugin


# --- Question 32: Debug Runner ---
def test_q32_runner_debug():
    """Question 32: Runner.run_debug."""
    assert hasattr(Runner, "run_debug")


# --- Question 33: Toolset Lifecycle ---
def test_q33_toolset_close():
    """Question 33: BaseToolset.close."""
    assert inspect.iscoroutinefunction(BaseToolset.close)


# --- Question 34: Affective Dialog ---
def test_q34_affective_dialog():
    """Question 34: RunConfig enable_affective_dialog."""
    config = RunConfig()
    assert hasattr(config, "enable_affective_dialog")


# --- Question 35: Credential Manager (New) ---
def test_q35_credential_manager():
    """Question 35: CredentialManager."""
    assert CredentialManager
    # Negative: AuthService
    import google.adk.auth.credential_manager as cm

    assert not hasattr(cm, "AuthService")


# --- Question 36: Telemetry Flag (New) ---
def test_q36_telemetry_flag():
    """Question 36: CLI trace flag."""
    params = cli_api_server.params
    trace_param = next((p for p in params if p.name == "trace_to_cloud"), None)
    assert trace_param is not None
    assert trace_param.is_flag


# --- Question 37: Persistence URI (New) ---
# (Implicit check, documentation based)


# --- Question 38: Deployment Flag (New) ---
def test_q38_deploy_flag():
    """Question 38: Cloud Run service name flag."""
    params = cli_deploy_cloud_run.params
    service_name_param = next((p for p in params if p.name == "service_name"), None)
    assert service_name_param is not None
    assert "--service_name" in service_name_param.opts


# --- Question 39: Multi-modal Input (New) ---
def test_q39_multimodal_input():
    """Question 39: Image input structure."""
    sig = inspect.signature(types.Part.__init__)
    assert "inline_data" in sig.parameters


# --- Question 40: Error Handling (New) ---
def test_q40_error_callback():
    """Question 40: on_tool_error_callback."""
    assert "on_tool_error_callback" in LlmAgent.model_fields


# --- Question 41: EvalCase (New) ---
def test_q41_eval_case_structure():
    """Question 41: EvalCase fields."""
    assert hasattr(EvalCase, "ensure_conversation_xor_conversation_scenario")


# --- Question 42: IntermediateData (New) ---
def test_q42_intermediate_data():
    """Question 42: IntermediateData fields."""
    type_hints = inspect.get_annotations(IntermediateData)
    assert "tool_uses" in type_hints
    assert "tool_responses" in type_hints
    assert "intermediate_responses" in type_hints


if __name__ == "__main__":
    print(f"Running verification script from: {__file__}")
    # Manually run all test functions if executed directly
    current_module = sys.modules[__name__]
    for name, func in inspect.getmembers(current_module, inspect.isfunction):
        if name.startswith("test_"):
            try:
                func()
                # print(f". {name} passed")
            except Exception as e:
                print(f"F {name} failed: {e}")
                import traceback

                traceback.print_exc()
                sys.exit(1)
    print("All verification tests passed!")
