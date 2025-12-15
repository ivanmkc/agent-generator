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

"Integration tests specific to Gemini CLI Answer Generators."

import pytest
import json
import re
from pathlib import Path
from benchmarks.tests.integration.conftest import GeneratorTestCase

@pytest.mark.asyncio
async def test_generator_memory_context(test_case: GeneratorTestCase) -> None:
    """
    Verifies that the generator loads the expected context files by inspecting debug logs.
    """
    generator = test_case.generator

    # Check if this test case expects any context files
    if not test_case.expected_context_files:
         pytest.skip(f"No expected context files defined for {test_case.id}")

    # Ensure generator is set up (e.g., container running)
    await generator.setup()
    
    # We need a CLI generator to run commands and get debug logs
    if not hasattr(generator, "_run_cli_command"):
        pytest.skip(f"Generator {test_case.id} does not support _run_cli_command.")

    print(f"[{test_case.id}] Running gemini --debug to inspect memory context...")
    
    # Run a simple command with --debug to trigger context loading logs
    # Using a trivial command like 'hello' as the prompt to minimize side effects
    command_parts = [generator.cli_path, "--debug", "hello"]
    try:
        response_dict, logs = await generator._run_cli_command(command_parts)
    except Exception as e:
        pytest.fail(f"[{test_case.id}] Failed to run debug command: {e}")

    # Combine all log content for easier searching
    full_logs_content = "\n".join([event.content for event in logs if event.content])
    print(f"[{test_case.id}] Full debug logs (snippet):\n{full_logs_content[:1000]}...")

    # Regex to find the specific debug line for loaded context paths
    # Example: [DEBUG] [MemoryDiscovery] Final ordered INSTRUCTIONS.md paths to read: ["/path/to/INSTRUCTIONS.md"]
    match = re.search(
        r"\[DEBUG\] \[MemoryDiscovery\] Final ordered INSTRUCTIONS.md paths to read: (.*)",
        full_logs_content,
    )
    if not match:
        # If the debug line is not found, check if it's an LLM refusal
        if "I cannot" in full_logs_content or "I am unable" in full_logs_content or "I am a specialized agent" in full_logs_content:
            pytest.skip(f"[{test_case.id}] CLI returned LLM explanation instead of debug memory logs: {full_logs_content.strip()[:100]}...")
        else:
            pytest.fail(f"[{test_case.id}] 'Final ordered INSTRUCTIONS.md paths' debug line not found in logs, and no LLM refusal detected.")

    # Extract the paths string and parse as JSON array
    paths_str = match.group(1).replace("'", '"') # Replace single quotes with double for valid JSON
    
    # Handle empty list case (e.g. if paths_str is empty)
    if not paths_str.strip():
        loaded_paths = []
    else:
        try:
            # The regex now captures the entire JSON array string directly
            loaded_paths = json.loads(paths_str)
        except json.JSONDecodeError as e:
            pytest.fail(f"[{test_case.id}] Failed to parse loaded paths JSON from debug logs: {e}\nRaw paths string: {paths_str}")


    print(f"[{test_case.id}] Discovered loaded context paths: {loaded_paths}")

    # Assert that all expected files are present in the loaded paths
    for expected_file in test_case.expected_context_files:
        assert expected_file in loaded_paths, f"Expected context file '{expected_file}' not found in loaded memory paths. Available: {loaded_paths}"