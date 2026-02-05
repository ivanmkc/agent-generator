"""
Integration Tests for `debug` command edge cases.

This module performs integration testing of the `mcp-manage debug` command against a 
real (locally spawned) MCP server instance. It specifically targets edge cases by 
feeding the server "poisoned" data (e.g., fields containing error-like strings) 
via a custom `ranked_targets.yaml`.

Scenarios covered:
- False positives in error detection when valid data mimics error messages.
- Robustness of the regex-based success checks.
"""

import pytest
import os
import sys
import yaml
import json
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch

# Ensure import works
sys.path.append(str(Path(__file__).parent.parent / "src"))

from adk_knowledge_ext import manage_mcp

@pytest.fixture
def runner():
    return CliRunner()

def strip_ansi(text):
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

@pytest.fixture
def create_test_env(tmp_path):
    """Factory fixture to create an environment with a custom index."""
    def _create(index_data):
        index_path = tmp_path / "ranked_targets.yaml"
        with open(index_path, "w") as f:
            yaml.dump(index_data, f)

        config_dir = tmp_path / ".gemini"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "settings.json"
        
        # Use file:// protocol for local path to satisfy curl in server
        kb_config_str = json.dumps([{
            "id": "test-kb",
            "repo_url": "https://example.com/test.git",
            "version": "v1",
            "index_url": f"file://{index_path}"
        }])
        
        settings = {
            "mcpServers": {
                "codebase-knowledge": {
                    "command": "uvx",
                    "args": [],
                    "env": {
                        "MCP_KNOWLEDGE_BASES": kb_config_str
                    }
                }
            }
        }
        
        with open(config_file, "w") as f:
            json.dump(settings, f)
            
        return config_file, index_path
    return _create

def run_debug_with_env(runner, config_path):
    """Helper to run the debug command with the setup env."""
    mock_ide_config = manage_mcp.IdeConfig(
        detect_path=config_path.parent,
        config_method="json",
        config_path=config_path,
        config_key="mcpServers",
        start_instruction="Test Instruction"
    )
    
    src_path = str(Path(__file__).parent.parent / "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = src_path
    
    with (
        patch.dict(manage_mcp.IDE_CONFIGS, {"TestIDE": mock_ide_config}, clear=True),
        patch("adk_knowledge_ext.manage_mcp._is_mcp_configured", return_value=True),
        patch.dict(os.environ, env)
    ):
        result = runner.invoke(manage_mcp.debug)
        
    return strip_ansi(result.output)

def test_edge_case_symbol_field_collision(create_test_env, runner):
    """
    Scenario: 'Symbol' Field Collision (False Positive Check)
    
    The server error message format is "Symbol '...' not found".
    This test creates a valid target with a custom field named 'Symbol' that contains 
    the text "not found".
    
    Goal: Verify that the `debug` command does NOT flag this valid target as a failure.
    It proves the regex check `^Symbol '.*' not found` is strict enough to avoid 
    matching `Symbol: This string contains not found`.
    """
    data = [{
        "rank": 1,
        "id": "test.Collision",
        "name": "Collision",
        "type": "CLASS",
        # This field mimics the start of the error message
        "Symbol": "This string contains not found", 
        "file_path": "src/test.py"
    }]
    
    config_path, _ = create_test_env(data)
    output = run_debug_with_env(runner, config_path)
    
    # We expect this to PASS (OK), proving our check is robust (or failing if it isn't)
    assert "inspect_symbol" in output
    assert "test.Collision" in output
    
    if "❌ Failed" in output:
        pytest.fail(f"False positive failure detected on 'Symbol' field collision.\nOutput:\n{output}")
    
    assert "✅ OK" in output

def test_edge_case_error_prefix_in_docstring(create_test_env, runner):
    """
    Scenario: 'Error:' Prefix in Docstring (False Positive Check)
    
    This test creates a valid target where the docstring starts exactly with "Error: ".
    Since `inspect_symbol` output is YAML, this content will be nested/indented.
    
    Goal: Verify that the `debug` command does NOT flag this as a failure.
    It proves the check `content.strip().startswith("Error:")` correctly targets 
    only top-level error messages, not nested content.
    """
    data = [{
        "rank": 1,
        "id": "test.ErrorPrefix",
        "name": "ErrorPrefix",
        "type": "CLASS",
        "docstring": "Error: This looks like an error but is a docstring.",
        "file_path": "src/test.py"
    }]
    
    config_path, _ = create_test_env(data)
    output = run_debug_with_env(runner, config_path)
    
    assert "✅ OK" in output
    assert "Output (Error)" not in output

if __name__ == "__main__":
    pass