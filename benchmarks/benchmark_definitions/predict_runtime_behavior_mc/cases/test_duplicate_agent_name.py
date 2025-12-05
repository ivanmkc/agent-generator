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

from google.adk.agents import LlmAgent
from google.adk.agents import SequentialAgent


# --8<-- [start:duplicate_agent_name]
def code_under_test():
  a1 = LlmAgent(name="worker", model="gemini-2.5-flash")
  a2 = LlmAgent(name="worker", model="gemini-2.5-flash")
  root = SequentialAgent(name="root", sub_agents=[a1, a2])
  return root


# --8<-- [end:duplicate_agent_name]


def test_duplicate_agent_name():
  """
  Validates behavior when creating a SequentialAgent with duplicate sub-agent names.
  """
  # Expected behavior: No error is raised when a SequentialAgent is created
  # with sub-agents that have duplicate names.

  root = code_under_test()
  assert len(root.sub_agents) == 2

  assert root.sub_agents[0].name == "worker"
  assert root.sub_agents[1].name == "worker"
