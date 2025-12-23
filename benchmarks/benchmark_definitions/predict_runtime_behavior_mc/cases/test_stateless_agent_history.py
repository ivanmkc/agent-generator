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


# --8<-- [start:stateless_agent_history]
def code_under_test():
    agent = LlmAgent(name="my_agent", model="gemini-2.5-flash", include_contents="none")
    return agent


# --8<-- [end:stateless_agent_history]


def test_stateless_agent_history():
    """
    Validates stateless agent init.
    """
    # Expected behavior: The LlmAgent is created successfully with
    # `include_contents` set to "none".
    agent = code_under_test()
    assert agent.include_contents == "none"
