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

"""Candidate ADK Agents for benchmarking."""

from google.adk.agents import LlmAgent


def create_default_adk_agent(model_name: str = "gemini-2.5-pro") -> LlmAgent:
  """Creates the default LlmAgent used for ADK benchmarking."""
  return LlmAgent(
      name="adk_test_agent",
      model=model_name,
      instruction=(
          "You are a senior engineer specializing in the ADK Python framework."
          " Your task is to answer questions or fix code with expert precision."
          " Always respond with a JSON object conforming to the specified"
          " schema, enclosed in a markdown code block (```json...```)."
      ),
  )
