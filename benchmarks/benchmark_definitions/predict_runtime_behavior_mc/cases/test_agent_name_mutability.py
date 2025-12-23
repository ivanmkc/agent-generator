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


# --8<-- [start:agent_name_mutability]
def code_under_test():
    agent = LlmAgent(name="a", model="gemini-2.5-flash")
    return agent


# --8<-- [end:agent_name_mutability]


def test_agent_name_mutability(capsys):
    """
    Validates agent name mutability.
    """
    # Expected behavior: The agent's name is mutable and can be changed after
    # initialization.
    agent = code_under_test()
    assert agent.name == "a"
    agent.name = "b"
    assert agent.name == "b"
