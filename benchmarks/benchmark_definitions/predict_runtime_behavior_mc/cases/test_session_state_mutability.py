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

from google.adk.sessions import Session


# --8<-- [start:session_state_mutability]
def code_under_test():
  from google.adk.sessions import Session

  session = Session(id="test_id", user_id="u1", app_name="test_app")
  session.state["my_key"] = "initial_value"
  assert session.state["my_key"] == "initial_value"
  session.state["my_key"] = "updated_value"
  return session


def test_session_properties(capsys):
  """
  Validates session properties.
  """
  session = code_under_test()
  assert session.state["my_key"] == "updated_value"
