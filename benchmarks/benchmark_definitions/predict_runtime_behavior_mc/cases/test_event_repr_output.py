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

from google.adk.events import Event
from pydantic import ValidationError
import pytest


# --8<-- [start:event_repr_output]
def code_under_test():
    Event(type="model_response", content="Hello")


# --8<-- [end:event_repr_output]


def test_event_repr_output():
    """
    Validates Event object creation failure (Predict Error).
    """
    # Expected behavior: A ValidationError is raised because `type` is not a
    # valid field for `Event`.
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        code_under_test()
