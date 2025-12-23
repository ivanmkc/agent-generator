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


# --8<-- [start:tool_session_id_injection]
def code_under_test():
    def my_tool(query: str, session_id: str):
        ...

    return my_tool


# --8<-- [end:tool_session_id_injection]


def test_tool_session_id_injection():
    """
    Validates tool signature.
    """
    # Expected behavior: The function signature is inspected, and it is
    # confirmed that `session_id` is a parameter.
    my_tool = code_under_test()
    assert "session_id" in my_tool.__annotations__
