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
import pytest


# --8<-- [start:agent_clone_invalid_field]
def code_under_test():
  agent = LlmAgent(name="test", model="gemini-2.5-flash")
  agent.clone(update={"unknown_field": 123})


# --8<-- [end:agent_clone_invalid_field]


def test_agent_clone_invalid_field():
  """
  Validates agent cloning with extra fields.
  """
  # Expected behavior: A ValueError is raised because `unknown_field` is not
  # a valid field for `LlmAgent`.
  with pytest.raises(ValueError, match="Cannot update nonexistent fields"):
    code_under_test()
