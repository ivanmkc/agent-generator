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

from google.adk.agents import LoopAgent


# --8<-- [start:loop_agent_empty_subagents]
def code_under_test():
  agent = LoopAgent(name="looper", sub_agents=[])
  return agent


# --8<-- [end:loop_agent_empty_subagents]


def test_loop_agent_empty_subagents():
  """
  Validates LoopAgent with empty sub_agents.
  """
  # Expected behavior: The LoopAgent is created successfully with an empty
  # `sub_agents` list.
  agent = code_under_test()
  assert len(agent.sub_agents) == 0
