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