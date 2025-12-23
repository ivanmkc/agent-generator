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
Verification script for api_understanding/benchmark.yaml.
"""

import inspect
from pathlib import Path
import sys

# Imports based on the "file" field in the benchmark YAML
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.apps.app import App
from google.adk.evaluation.agent_evaluator import AgentEvaluator
from google.adk.events.event import Event
from google.adk.models.base_llm import BaseLlm
from google.adk.models.registry import LLMRegistry
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.plugins.global_instruction_plugin import GlobalInstructionPlugin
from google.adk.plugins.logging_plugin import LoggingPlugin
from google.adk.plugins.plugin_manager import PluginManager
from google.adk.runners import InMemoryRunner
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.session import Session
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools.tool_configs import ToolConfig
from google.adk.tools.tool_context import ToolContext
import pytest


def test_base_agent():
    # Q: Foundational class? A: BaseAgent
    assert BaseAgent
    # Q: Mandatory param? A: name
    assert "name" in BaseAgent.model_fields
    # Q: run_async?
    assert hasattr(BaseAgent, "run_async")
    # Q: callbacks?
    assert "before_agent_callback" in BaseAgent.model_fields
    assert "after_agent_callback" in BaseAgent.model_fields
    # Q: find_agent?
    assert hasattr(BaseAgent, "find_agent")


def test_sequential_agent():
    # Q: Sequence of agents? A: SequentialAgent
    assert SequentialAgent


def test_runner():
    # Q: Entry point? A: Runner
    assert Runner


def test_base_llm():
    # Q: Core interface for LLM? A: BaseLlm
    assert BaseLlm


def test_agent_evaluator():
    # Q: evaluate method?
    assert hasattr(AgentEvaluator, "evaluate")


def test_loop_agent():
    # Q: max_iterations?
    assert "max_iterations" in LoopAgent.model_fields


def test_llm_agent():
    # Q: model param?
    assert "model" in LlmAgent.model_fields
    # Q: generate_content_config?
    assert "generate_content_config" in LlmAgent.model_fields
    # Q: tools param?
    assert "tools" in LlmAgent.model_fields
    # Q: before_model_callback?
    assert "before_model_callback" in LlmAgent.model_fields
    # Q: output_key?
    assert "output_key" in LlmAgent.model_fields
    # Q: output_schema?
    assert "output_schema" in LlmAgent.model_fields
    # Q: static_instruction?
    assert "static_instruction" in LlmAgent.model_fields


def test_llm_registry():
    # Q: register method?
    assert hasattr(LLMRegistry, "register")


def test_base_plugin():
    # Q: Foundational class? A: BasePlugin
    assert BasePlugin
    # Q: before_agent_callback returns value?
    # (Hard to verify logic without running, but existence is checked)
    assert hasattr(BasePlugin, "before_agent_callback")


def test_plugin_manager():
    # Q: Invoking callbacks? A: PluginManager
    assert PluginManager


def test_logging_plugin():
    # Q: Observational plugin? A: LoggingPlugin
    assert LoggingPlugin


def test_global_instruction_plugin():
    # Q: System-wide instruction? A: GlobalInstructionPlugin
    assert GlobalInstructionPlugin


def test_invocation_context():
    # Q: set_agent_state?
    assert hasattr(InvocationContext, "set_agent_state")
    # Q: What is InvocationContext? (Concept check)
    assert InvocationContext


def test_base_session_service():
    # Q: Abstract base class? A: BaseSessionService
    assert BaseSessionService
    # Q: append_event?
    assert hasattr(BaseSessionService, "append_event")


def test_callback_context():
    # Q: What is CallbackContext?
    assert CallbackContext


def test_session():
    # Q: Session data model?
    assert Session


def test_tool_context():
    # Q: Access services? A: ToolContext
    assert ToolContext


def test_function_tool():
    # Q: Create tool from function? A: FunctionTool
    assert FunctionTool


def test_tool_config():
    # Q: Configure tools in YAML? A: ToolConfig
    assert ToolConfig


def test_base_toolset():
    # Q: Manage collection of tools? A: BaseToolset
    assert BaseToolset


def test_google_search_tool():
    # Q: Native search? A: GoogleSearchTool
    assert GoogleSearchTool
    # Verify it inherits from BaseTool
    assert issubclass(GoogleSearchTool, BaseTool)


def test_parallel_agent():
    # Q: Run concurrent? A: ParallelAgent
    assert ParallelAgent


def test_app():
    # Q: Add plugins? A: App
    assert App


def test_event():
    # Q: Conversation history structure? A: Event
    assert Event


def test_in_memory_runner():
    # Q: Local dev runner? A: InMemoryRunner
    assert InMemoryRunner


def test_base_tool():
    # Q: Base class for tools? A: BaseTool
    assert BaseTool


if __name__ == "__main__":
    # Manually run tests if executed directly
    current_module = sys.modules[__name__]
    for name, func in inspect.getmembers(current_module, inspect.isfunction):
        if name.startswith("test_"):
            try:
                func()
            except Exception as e:
                print(f"F {name} failed: {e}")
                import traceback

                traceback.print_exc()
                sys.exit(1)
    print("All verification tests passed!")
