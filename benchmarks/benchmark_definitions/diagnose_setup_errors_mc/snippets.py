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
Test file containing code snippets for 'diagnose_setup_errors_mc' benchmarks.
These snippets are intentionally buggy or incomplete to test error diagnosis.
"""

import sys

from google.adk.agents import LlmAgent
from google.adk.agents import LoopAgent
from google.adk.agents import ParallelAgent
from google.adk.agents import SequentialAgent
from google.adk.agents.run_config import RunConfig
from google.adk.apps import App
from google.adk.apps.events_compaction import EventsCompactionConfig
from google.adk.runners import Runner
from google.adk.sessions import ContextCacheConfig
from google.adk.tools import BuiltInCodeExecutor
from google.genai import types
from pydantic import BaseModel
from pydantic import ValidationError
import pytest


# Mock classes/functions for context
def calculate_tax():
  pass


class UserInfo(BaseModel):
  name: str
  age: int


class MyPydanticModel(BaseModel):
  field: str


ThinkingConfig = object  # Dummy


# --8<-- [start:missing_model_arg]
def snippet_agent_creation_issue_1(**kwargs):
  root_agent = LlmAgent(
      name="my_agent", instruction="You are a helpful assistant.", **kwargs
  )


# --8<-- [end:missing_model_arg]


def test_missing_model_arg():
  """Snippet: missing model argument in LlmAgent."""
  # Expect: ValidationError because 'model' field is required for LlmAgent.
  with pytest.raises(ValidationError):
    snippet_agent_creation_issue_1()


# --8<-- [start:raw_function_tool]
def snippet_raw_function_tool():
  root_agent = LlmAgent(
      name="tax_agent", model="gemini-2.5-flash", tools=[calculate_tax]
  )


# --8<-- [end:raw_function_tool]


def test_raw_function_tool():
  """Snippet: passing raw function instead of FunctionTool."""
  # Expect: ValueError or similar because raw functions must be wrapped in FunctionTool.
  with pytest.raises(Exception):
    snippet_raw_function_tool()


# --8<-- [start:sequential_agent_tools]
def snippet_sequential_agent_tools():
  agent_one = LlmAgent(name="one", model="gemini-2.5-flash")
  agent_two = LlmAgent(name="two", model="gemini-2.5-flash")
  kwargs = {"tools": [agent_one, agent_two]}
  root_agent = SequentialAgent(name="sequence", **kwargs)


# --8<-- [end:sequential_agent_tools]


def test_sequential_agent_tools():
  """Snippet: using tools param instead of sub_agents in SequentialAgent."""
  with pytest.raises(Exception):
    snippet_sequential_agent_tools()


# --8<-- [start:code_executor_in_tools]
def snippet_code_executor_in_tools():
  from google.adk.tools import BuiltInCodeExecutor as Executor

  tool_instance = Executor()
  kwargs = {"tools": [tool_instance]}
  root_agent = LlmAgent(name="coder", model="gemini-2.5-flash", **kwargs)


# --8<-- [end:code_executor_in_tools]


def test_code_executor_in_tools():
  """Snippet: passing BuiltInCodeExecutor in tools list."""
  with pytest.raises(Exception):
    snippet_code_executor_in_tools()


# --8<-- [start:delegation_in_tools]
def snippet_delegation_in_tools():
  specialist_agent = LlmAgent(
      name="specialist", model="gemini-2.5-flash", description="Spec"
  )
  root_agent = LlmAgent(
      name="manager", model="gemini-2.5-flash", tools=[specialist_agent]
  )


# --8<-- [end:delegation_in_tools]


def test_delegation_in_tools():
  """Snippet: passing agent in tools list for delegation."""
  with pytest.raises(Exception):
    snippet_delegation_in_tools()


# --8<-- [start:invalid_multi_agent_class]
def snippet_invalid_multi_agent_class():
  agent_a = LlmAgent(name="a", model="gemini-2.5-flash")
  agent_b = LlmAgent(name="b", model="gemini-2.5-flash")
  root_agent = MultiAgent(name="my_group", agents=[agent_a, agent_b])


# --8<-- [end:invalid_multi_agent_class]


def test_invalid_multi_agent_class():
  """Snippet: using non-existent MultiAgent class."""
  with pytest.raises(NameError):
    snippet_invalid_multi_agent_class()


# --8<-- [start:input_schema_instance]
def snippet_input_schema_instance():
  class UserInfo(BaseModel):
    name: str
    age: int

  my_obj = UserInfo()
  kwargs = {"input_schema": my_obj}
  root_agent = LlmAgent(name="form_filler", model="gemini-2.5-flash", **kwargs)


# --8<-- [end:input_schema_instance]


def test_input_schema_instance():
  """Snippet: passing instance instead of class to input_schema."""
  with pytest.raises(Exception):
    snippet_input_schema_instance()


# --8<-- [start:output_schema_params]
def snippet_output_schema_params():
  root_agent = LlmAgent(
      name="json_agent",
      model="gemini-2.5-flash",
      output_format="json",
      format_spec=MyPydanticModel,
  )


# --8<-- [end:output_schema_params]


def test_output_schema_params():
  """Snippet: using incorrect parameters for output schema."""
  with pytest.raises(Exception):
    snippet_output_schema_params()


# --8<-- [start:invalid_agent_name_hyphen]
def snippet_agent_name_check_1():
  agent = LlmAgent(name="my-agent", model="gemini-1.5-pro")


# --8<-- [end:invalid_agent_name_hyphen]


def test_invalid_agent_name_hyphen():
  """Snippet: agent name with hyphen."""
  with pytest.raises(ValueError):
    snippet_agent_name_check_1()


# --8<-- [start:gen_config_sys_instr]
def snippet_gen_config_sys_instr():
  agent = LlmAgent(
      name="agent",
      model="gemini-1.5-pro",
      generate_content_config=types.GenerateContentConfig(
          system_instruction="Hi"
      ),
  )


# --8<-- [end:gen_config_sys_instr]


def test_gen_config_sys_instr():
  """Snippet: system_instruction in generate_content_config."""
  with pytest.raises(ValueError):
    snippet_gen_config_sys_instr()


# --8<-- [start:gen_config_tools]
def snippet_gen_config_tools():
  agent = LlmAgent(
      name="agent",
      model="gemini-1.5-pro",
      generate_content_config=types.GenerateContentConfig(
          tools=[calculate_tax]
      ),
  )


# --8<-- [end:gen_config_tools]


def test_gen_config_tools():
  """Snippet: tools in generate_content_config."""
  with pytest.raises(ValueError):
    snippet_gen_config_tools()


# --8<-- [start:gen_config_response_schema]
def snippet_gen_config_response_schema():
  agent = LlmAgent(
      name="agent",
      model="gemini-1.5-pro",
      generate_content_config=types.GenerateContentConfig(
          response_schema=MyPydanticModel
      ),
  )


# --8<-- [end:gen_config_response_schema]


def test_gen_config_response_schema():
  """Snippet: response_schema in generate_content_config."""
  with pytest.raises(ValueError):
    snippet_gen_config_response_schema()


# --8<-- [start:runner_app_and_agent]
def snippet_runner_app_and_agent():
  agent_one = LlmAgent(name="one", model="gemini-2.5-flash")
  my_app = App(name="my_app", root_agent=agent_one)
  my_agent = agent_one
  runner = Runner(app=my_app, agent=my_agent)


# --8<-- [end:runner_app_and_agent]


def test_runner_app_and_agent():
  """Snippet: initializing Runner with both app and agent."""
  with pytest.raises(ValueError):
    snippet_runner_app_and_agent()


# --8<-- [start:runner_no_app_no_name]
def snippet_runner_init_check_1():
  my_agent = LlmAgent(name="agent", model="gemini-2.5-flash")
  runner = Runner(agent=my_agent)


# --8<-- [end:runner_no_app_no_name]


def test_runner_no_app_no_name():
  """Snippet: initializing Runner with agent but no app_name."""
  with pytest.raises(ValueError):
    snippet_runner_init_check_1()


# --8<-- [start:invalid_app_name]
def snippet_app_case_16():
  agent = LlmAgent(name="agent", model="gemini-2.5-flash")
  kwargs = {"name": "my app"}
  app = App(root_agent=agent, **kwargs)


# --8<-- [end:invalid_app_name]


def test_invalid_app_name():
  """Snippet: invalid app name with spaces."""
  with pytest.raises(ValueError):
    snippet_app_case_16()


# --8<-- [start:clone_parent_agent]
def snippet_clone_parent_agent():
  agent = LlmAgent(name="agent", model="gemini-2.5-flash")
  other_agent = LlmAgent(name="other", model="gemini-2.5-flash")
  new_agent = agent.clone(update={"parent_agent": other_agent})


# --8<-- [end:clone_parent_agent]


def test_clone_parent_agent():
  """Snippet: attempting to update parent_agent in clone."""
  with pytest.raises(ValueError):
    snippet_clone_parent_agent()


# --8<-- [start:clone_unknown_field]
def snippet_clone_unknown_field():
  agent = LlmAgent(name="agent", model="gemini-2.5-flash")
  new_agent = agent.clone(update={"random_field": 123})


# --8<-- [end:clone_unknown_field]


def test_clone_unknown_field():
  """Snippet: attempting to update unknown field in clone."""
  with pytest.raises(ValueError):
    snippet_clone_unknown_field()


# --8<-- [start:sequential_empty_subagents]
def snippet_sequential_empty_subagents():
  agent = SequentialAgent(name="seq")


# --8<-- [end:sequential_empty_subagents]


def test_sequential_empty_subagents():
  """Snippet: SequentialAgent with no sub_agents."""
  snippet_sequential_empty_subagents()


# --8<-- [start:shared_agent_ownership]
def snippet_shared_agent_ownership():
  child = LlmAgent(name="child", model="gemini-2.5-flash")
  parent1 = SequentialAgent(name="p1", sub_agents=[child])

  parent2 = SequentialAgent(name="p2", sub_agents=[child])


# --8<-- [end:shared_agent_ownership]


def test_shared_agent_ownership():
  """Snippet: adding same agent to multiple parents."""
  with pytest.raises(ValueError):
    snippet_shared_agent_ownership()


# --8<-- [start:gen_config_thinking]
def snippet_gen_config_thinking():
  agent = LlmAgent(
      name="a",
      model="m",
      generate_content_config=types.GenerateContentConfig(thinking_config=...),
  )


# --8<-- [end:gen_config_thinking]


def test_gen_config_thinking():
  """Snippet: thinking_config in generate_content_config."""
  with pytest.raises(ValueError):
    snippet_gen_config_thinking()


# --8<-- [start:run_config_max_calls_overflow]
def snippet_run_config_check_limit():
  val = -1
  config = RunConfig(max_llm_calls=val)


# --8<-- [end:run_config_max_calls_overflow]


def test_run_config_max_calls_overflow():
  """Snippet: max_llm_calls overflow."""
  with pytest.raises(ValueError):
    snippet_run_config_check_limit()


# --8<-- [start:loop_agent_missing_max_iter]
def snippet_loop_agent_missing_max_iter():
  child = LlmAgent(name="child", model="gemini-2.5-flash")
  agent = LoopAgent(name="loop", sub_agents=[child])


# --8<-- [end:loop_agent_missing_max_iter]


def test_loop_agent_missing_max_iter():
  """Snippet: LoopAgent without max_iterations."""
  snippet_loop_agent_missing_max_iter()


# --8<-- [start:set_parent_agent_init]
def snippet_set_parent_agent_init():
  parent = LlmAgent(name="parent", model="gemini-2.5-flash")
  agent = LlmAgent(name="child", parent_agent=parent)


# --8<-- [end:set_parent_agent_init]


def test_set_parent_agent_init():
  """Snippet: setting parent_agent in init."""
  with pytest.raises((TypeError, ValueError)):
    snippet_set_parent_agent_init()


# --8<-- [start:cache_ttl_string]
def snippet_cache_ttl_string():
  config = ContextCacheConfig(ttl="3600s")


# --8<-- [end:cache_ttl_string]


def test_cache_ttl_string():
  """Snippet: ContextCacheConfig ttl as string."""
  with pytest.raises(ValidationError):
    snippet_cache_ttl_string()


# --8<-- [start:app_extra_args]
def snippet_app_extra_args():
  root = LlmAgent(name="root", model="gemini-2.5-flash")
  app = App(name="app", root_agent=root, agents=[root])


# --8<-- [end:app_extra_args]


def test_app_extra_args():
  """Snippet: App with invalid extra args."""
  with pytest.raises(ValidationError):
    snippet_app_extra_args()


# --8<-- [start:compaction_overlap_negative]
def snippet_compaction_overlap_negative():
  EventsCompactionConfig(overlap_size=-1)


# --8<-- [end:compaction_overlap_negative]


def test_compaction_overlap_negative():
  """Snippet: EventsCompactionConfig overlap_size negative."""
  with pytest.raises(ValidationError):
    snippet_compaction_overlap_negative()


# --8<-- [start:compaction_interval_zero]
def snippet_compaction_interval_zero():
  EventsCompactionConfig(compaction_interval=0)


# --8<-- [end:compaction_interval_zero]


def test_compaction_interval_zero():
  """Snippet: EventsCompactionConfig compaction_interval zero."""
  with pytest.raises(ValidationError):
    snippet_compaction_interval_zero()


# --8<-- [start:compaction_summarizer_string]
def snippet_compaction_summarizer_string():
  EventsCompactionConfig(summarizer="string")


# --8<-- [end:compaction_summarizer_string]


def test_compaction_summarizer_string():
  """Snippet: EventsCompactionConfig summarizer as string."""
  with pytest.raises(ValidationError):
    snippet_compaction_summarizer_string()


# --8<-- [start:parallel_max_workers_string]
def snippet_parallel_max_workers_string():
  agent = ParallelAgent(name="p", max_workers="10")


# --8<-- [end:parallel_max_workers_string]


def test_parallel_max_workers_string():
  """Snippet: ParallelAgent max_workers as string."""
  with pytest.raises(ValidationError):
    snippet_parallel_max_workers_string()
