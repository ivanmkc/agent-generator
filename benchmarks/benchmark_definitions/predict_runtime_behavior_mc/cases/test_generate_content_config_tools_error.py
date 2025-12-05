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
from google.genai import types
from pydantic import ValidationError
import pytest


# --8<-- [start:generate_content_config_tools_error]
def code_under_test():
  my_tool = lambda: None
  gen_config = types.GenerateContentConfig(tools=[my_tool])
  LlmAgent(
      name="agent",
      model="gemini-2.5-flash",
      generate_content_config=gen_config,
  )


# --8<-- [end:generate_content_config_tools_error]


def test_generate_content_config_tools_error():
  """
  Validates that tools in generate_content_config raises ValidationError.
  """
  # Expected behavior: A ValidationError is raised because `tools` is not a valid
  # field in `GenerateContentConfig`.
  with pytest.raises(
      ValidationError, match="All tools must be set via LlmAgent.tools"
  ):
    code_under_test()
