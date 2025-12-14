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

"""
Primary unified integration test suite for all Answer Generator implementations.
"""

import re # Import re for regex parsing
import pytest
import json
from pathlib import Path
# Import for type hinting; pytest automatically finds fixtures in conftes
from benchmarks.tests.integration.conftest import GeneratorTestCase

@pytest.mark.asyncio
async def test_generator_capabilities(test_case: GeneratorTestCase) -> None:
    """
    Verifies that the generator discovers extensions and MCP tools if supported.
    """
    generator = test_case.generator
    
    # Track if we performed any checks to decide whether to skip at the end
    checks_performed = False

    # 1. Gemini CLI Extensions Check
    if hasattr(generator, "get_gemini_cli_extensions"):
        checks_performed = True
        print(f"[{test_case.id}] Fetching Gemini CLI extensions...")
        actual_exts = await generator.get_gemini_cli_extensions()
        print(f"[{test_case.id}] Discovered extensions: {actual_exts}")

        for expected in test_case.expected_gemini_cli_extensions:
            assert any(expected in t for t in actual_exts), \
                f"[{test_case.id}] Expected CLI extension '{expected}' not found. Available: {actual_exts}"
    elif test_case.expected_gemini_cli_extensions:
        pytest.fail(f"[{test_case.id}] Configured to expect extensions {test_case.expected_gemini_cli_extensions}, but generator does not support 'get_gemini_cli_extensions'.")


    # 2. MCP Tools Check
    if hasattr(generator, "get_mcp_tools"):
        checks_performed = True
        print(f"[{test_case.id}] Fetching MCP tools...")
        actual_mcp = await generator.get_mcp_tools()
        print(f"[{test_case.id}] Discovered MCP tools: {actual_mcp}")

        for expected in test_case.expected_mcp_tools:
            assert any(expected in t for t in actual_mcp), \
                f"[{test_case.id}] Expected MCP tool '{expected}' not found. Available: {actual_mcp}"
    elif test_case.expected_mcp_tools:
        pytest.fail(f"[{test_case.id}] Configured to expect MCP tools {test_case.expected_mcp_tools}, but generator does not support 'get_mcp_tools'.")

    
    if not checks_performed:
        pytest.skip(f"Generator {test_case.id} supports neither CLI extensions nor MCP tool discovery.")


@pytest.mark.asyncio
async def test_generator_execution(test_case: GeneratorTestCase, tmp_path: Path) -> None:
    """
    Runs a real generation request using the specific case defined in TestCase.
    """
    generator = test_case.generator
    case = test_case.custom_case
    
    print(f"[{test_case.id}] Generating answer for case: '{case.get_identifier()}'")

    try:
        answer = await generator.generate_answer(case)

        # Basic Checks
        assert answer is not None
        assert answer.output is not None
        
        # Verify output type matches the benchmark case type using the case's validation method
        try:
            case.validate_answer_format(answer.output)
        except AssertionError as e:
            pytest.fail(f"Answer validation failed: {e}")

        # Trace Log Checks
        if answer.trace_logs and test_case.trace_indicators:
            logs_str = json.dumps([t.model_dump() for t in answer.trace_logs], default=str).lower()
            
            # Check for indicators
            found = any(ind.lower() in logs_str for ind in test_case.trace_indicators)
            
            if not found:
                # Dump logs to file for debugging
                log_file = tmp_path / f"{test_case.id}_debug_trace.json"
                with open(log_file, "w") as f:
                    f.write(logs_str)
                print(f"[{test_case.id}] Debug traces saved to {log_file}")
                
                pytest.fail(f"[{test_case.id}] Trace logs missing expected indicators: {test_case.trace_indicators}")
        
        elif not answer.trace_logs:
             print(f"[{test_case.id}] Warning: No trace logs returned.")

    except Exception as e:
        pytest.fail(f"[{test_case.id}] Generation failed: {e}")


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
    # Example: [DEBUG] [MemoryDiscovery] Final ordered GEMINI.md paths to read: ["/path/to/GEMINI.md"]
    match = re.search(
        r"\[DEBUG\] \[MemoryDiscovery\] Final ordered GEMINI\.md paths to read: \[(.*?)\]",
        full_logs_content,
    )

    if not match:
        pytest.fail(f"[{test_case.id}] 'Final ordered GEMINI.md paths' debug line not found in logs.")

    # Extract the paths string and parse as JSON array
    paths_str = match.group(1).replace("'", "\"") # Replace single quotes with double for valid JSON
    
    # Handle empty list case (e.g. if paths_str is empty)
    if not paths_str.strip():
        loaded_paths = []
    else:
        try:
            loaded_paths = json.loads(f"[{paths_str}]")
        except json.JSONDecodeError as e:
            pytest.fail(f"[{test_case.id}] Failed to parse loaded paths JSON from debug logs: {e}\nRaw paths string: {paths_str}")


    print(f"[{test_case.id}] Discovered loaded context paths: {loaded_paths}")

    # Assert that all expected files are present in the loaded paths
    for expected_file in test_case.expected_context_files:
        assert expected_file in loaded_paths, f"Expected context file '{expected_file}' not found in loaded memory paths. Available: {loaded_paths}"