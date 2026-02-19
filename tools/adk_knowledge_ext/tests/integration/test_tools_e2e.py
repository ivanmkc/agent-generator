"""
Targeted End-to-End (E2E) Tests for MCP Tools.

This module validates the functionality of individual MCP tools (`list_modules`, `inspect_symbol`)
by spinning up a real instance of the `adk_knowledge_ext.server` in a subprocess and
connecting to it via the standard IO client.

It uses a custom, temporary `ranked_targets.yaml` index to ensure deterministic results,
verifying that:
1. The server correctly loads custom indices provided via environment configuration.
2. Tools return the expected data format and content.
3. Logical errors (e.g., missing symbols) return the expected descriptive messages.
"""

import pytest
import os
import sys
import yaml
import json
import asyncio
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Ensure import works
sys.path.append(str(Path(__file__).parents[2] / "src"))

@pytest.fixture
def test_data(tmp_path):
    """Setup custom index and config for E2E tool testing."""
    index_data = [
        {
            "rank": 1,
            "id": "test.TargetOne",
            "name": "TargetOne",
            "type": "CLASS",
            "docstring": "Description of TargetOne.",
            "file_path": "src/test.py"
        },
        {
            "rank": 2,
            "id": "test.TargetTwo",
            "name": "TargetTwo",
            "type": "CLASS",
            "docstring": "Description of TargetTwo.",
            "file_path": "src/test.py"
        }
    ]
    index_path = tmp_path / "ranked_targets.yaml"
    with open(index_path, "w") as f:
        yaml.dump(index_data, f)
        
    return index_path

@pytest.mark.asyncio
async def test_tool_list_modules_e2e(test_data, tmp_path):
    """
    Scenario: List Modules E2E
    
    Verifies that `list_modules`:
    1. Connects to the server initialized with a custom local index.
    2. Returns a text response containing the formatted list of modules.
    3. Correctly parses and displays ranks, types, and IDs from the index.
    """
    
    # Configure environment for the server subprocess
    env = os.environ.copy()
    kb_config = [{
        "id": "test-kb",
        "repo_url": "https://example.com/test.git",
        "version": "v1",
        "index_url": f"file://{test_data}"
    }]
    env["MCP_KNOWLEDGE_BASES"] = json.dumps(kb_config)
    env["PYTHONPATH"] = str(Path(__file__).parents[2] / "src")
    env["HOME"] = str(tmp_path)
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "adk_knowledge_ext.server"],
        env=env
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Targeted Tool Call
            result = await session.call_tool("list_modules", arguments={"kb_id": "test-kb", "page_size": 2})
            
            assert not result.isError
            content = result.content[0].text
            assert "--- Ranked Modules in 'test-kb' (Page 1) ---" in content
            assert "[1] CLASS: test.TargetOne" in content
            assert "[2] CLASS: test.TargetTwo" in content

@pytest.mark.asyncio
async def test_tool_inspect_symbol_e2e(test_data, tmp_path):
    """
    Scenario: Inspect Symbol E2E
    
    Verifies that `inspect_symbol`:
    1. Returns the correct YAML structure for a valid symbol (Success Case).
    2. Returns a descriptive error message for a missing symbol (Logical Failure Case).
    3. Does NOT crash (isError=False) on logical failures, matching expected server behavior.
    """
    
    env = os.environ.copy()
    kb_config = [{
        "id": "test-kb",
        "repo_url": "https://example.com/test.git",
        "version": "v1",
        "index_url": f"file://{test_data}"
    }]
    env["MCP_KNOWLEDGE_BASES"] = json.dumps(kb_config)
    env["PYTHONPATH"] = str(Path(__file__).parents[2] / "src")
    env["HOME"] = str(tmp_path)
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "adk_knowledge_ext.server"],
        env=env
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Targeted Tool Call: Successful lookup
            result = await session.call_tool("inspect_symbol", arguments={"kb_id": "test-kb", "fqn": "test.TargetOne"})
            
            assert not result.isError
            content = result.content[0].text
            # Parse YAML response
            parsed = yaml.safe_load(content)
            assert parsed["id"] == "test.TargetOne"
            assert parsed["docstring"] == "Description of TargetOne."
            
            # Targeted Tool Call: Missing symbol
            result_fail = await session.call_tool("inspect_symbol", arguments={"kb_id": "test-kb", "fqn": "test.Missing"})
            
            assert not result_fail.isError # MCP Success, but logical failure
            content_fail = result_fail.content[0].text
            assert "Symbol 'test.Missing' not found in index 'test-kb'." in content_fail

if __name__ == "__main__":
    pass
