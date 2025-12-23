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
from pydantic import ValidationError
import pytest


# --8<-- [start:llm_agent_name_validation]
def code_under_test():
    try:
        LlmAgent(name="my agent", model="gemini-2.5-flash")
    except ValueError as e:
        return str(e)  # Return the error message
    except TypeError as e:
        return str(e)
    return "No error"


# --8<-- [end:llm_agent_name_validation]


def test_llm_agent_name_validation():
    """
    Validates agent name regex constraints (Predict Output).
    """
    # Expected behavior: A ValidationError is raised because the agent name
    # contains a space.
    result = code_under_test()
    assert "Agent name must be a valid identifier." in result
