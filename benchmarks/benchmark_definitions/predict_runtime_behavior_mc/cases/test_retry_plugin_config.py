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
from google.adk.apps import App
from google.adk.plugins import ReflectAndRetryToolPlugin as MyPlugin


# --8<-- [start:retry_plugin_config]
def code_under_test():
    my_agent = LlmAgent(name="dummy", model="gemini-2.5-flash")
    app = App(
        name="my_app",
        root_agent=my_agent,
        plugins=[MyPlugin()],
    )
    return app


# --8<-- [end:retry_plugin_config]


def test_retry_plugin_config():
    """
    Validates ReflectAndRetryToolPlugin initialization.
    """
    # Expected behavior: The App is created with the ReflectAndRetryToolPlugin.
    app = code_under_test()
    assert len(app.plugins) == 1
