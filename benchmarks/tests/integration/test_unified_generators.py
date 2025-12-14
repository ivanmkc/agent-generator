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
    Verifies that the generator can load context from memory using /memory list.
    We try to set up a custom context file if possible (Podman only).
    """
    generator = test_case.generator
    
    # We only test this on Podman generators for now as we can control the container env
    if "GeminiCliPodmanAnswerGenerator" not in generator.__class__.__name__:
        pytest.skip("Skipping memory context test for non-Podman generator.")

    # Ensure generator is set up so container is running
    if not generator._setup_completed:
        await generator.setup()

    # We need to access the container name to inject files
    if not hasattr(generator, "_container_name") or not generator._container_name:
        pytest.skip("Generator does not have an active container name.")

    import subprocess
    container_name = generator._container_name
    
    print(f"[{test_case.id}] Injecting custom context into container {container_name}...")
    
    # 1. Create CUSTOM_CONTEXT.md
    custom_content = "# Custom Context\nThis is a custom context file for testing."
    try:
        subprocess.run(
            ["podman", "exec", container_name, "sh", "-c", f"echo '{custom_content}' > /repos/CUSTOM_CONTEXT.md"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to inject custom context file: {e.stderr.decode()}")
    
    # 2. Configure settings.json to use CUSTOM_CONTEXT.md
    # We assume /root/.gemini/ exists (created in Dockerfile)
    settings_json = json.dumps({"context": {"fileName": "CUSTOM_CONTEXT.md"}})
    try:
        subprocess.run(
            ["podman", "exec", container_name, "sh", "-c", f"echo '{settings_json}' > /root/.gemini/settings.json"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to inject settings.json: {e.stderr.decode()}")
    
    # 3. Run /memory list
    print(f"[{test_case.id}] Running /memory list...")
    if hasattr(generator, "_run_cli_command"):
        # Pass full command parts: gemini /memory list
        # We assume generator.cli_path is 'gemini'
        response, logs = await generator._run_cli_command([generator.cli_path, "/memory", "list"])
        
        stdout = response.get("stdout", "")
        print(f"[{test_case.id}] /memory list output:\n{stdout}")
        
        # Verify CUSTOM_CONTEXT.md is found
        assert "CUSTOM_CONTEXT.md" in stdout, f"Custom context file not found in /memory list output: {stdout}"
        
        # 4. Verify content with /memory show
        print(f"[{test_case.id}] Running /memory show...")
        response_show, _ = await generator._run_cli_command([generator.cli_path, "/memory", "show"])
        stdout_show = response_show.get("stdout", "")
        print(f"[{test_case.id}] /memory show output (snippet):\n{stdout_show[:500]}")
        
        assert "This is a custom context file for testing" in stdout_show, "Custom context content not found in /memory show output"