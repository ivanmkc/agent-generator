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


# --8<-- [start:callback_execution_order]
def code_under_test():
  async def cb1(agent, input):
    print("Pre")

  async def cb2(agent, input, response):
    print("Post")

  agent = LlmAgent(
      name="callback_agent",
      model="gemini-2.5-flash",
      before_agent_callback=cb1,
      after_agent_callback=cb2,
  )
  return agent, cb1, cb2


@pytest.mark.asyncio
async def test_callback_execution_order():
  """
  Validates callback execution order.
  """

  agent, pre, post = code_under_test()

  # This test only validates that the callbacks are attached correctly.
  # The actual execution order is tested in the `fix_errors` benchmark.
  assert agent.before_agent_callback == pre
  assert agent.after_agent_callback == post
