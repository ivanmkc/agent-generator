"""
Unit tests for the MCP Management CLI (manage_mcp.py).

This module consolidates tests for:
- Basic CLI command logic (setup, remove, debug).
- Logic for fetching existing KBs from configs.
- Diagnostic/Debug command edge cases (Symbol not found, etc.).
- Interactive prompts and confirmation flows.
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open, AsyncMock
from click.testing import CliRunner
import json
import os
import re

import yaml
import shutil
from pathlib import Path

from adk_knowledge_ext import manage_mcp
from adk_knowledge_ext.manage_mcp import KBDefinition

@pytest.fixture
def runner():
    return CliRunner()

# --- Basic Config Logic Tests ---

def test_get_existing_kbs_from_configs_no_config():
    with patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {}):
        kbs = manage_mcp._get_existing_kbs_from_configs()
        assert kbs == []

def test_get_existing_kbs_from_configs_with_config():
    mock_config = {
        "mcpServers": {
            "codebase-knowledge": {
                "command": "uvx",
                "args": [],
                "env": {
                    "MCP_KNOWLEDGE_BASES": json.dumps(
                        [{"id": "test/repo@v1", "repo_url": "url", "version": "v1"}]
                    )
                },
            }
        }
    }
    
    # Create a mock object that mimics IdeConfig attribute access
    mock_ide_info = MagicMock()
    mock_ide_info.config_method = "json"
    mock_ide_info.config_path = MagicMock()
    mock_ide_info.config_path.exists.return_value = True
    mock_ide_info.config_key = "mcpServers"
    
    mock_ide_configs = {
        "TestIDE": mock_ide_info
    }

    with (patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", mock_ide_configs), 
          patch("builtins.open", mock_open(read_data=json.dumps(mock_config)))):
        
        kbs = manage_mcp._get_existing_kbs_from_configs()
        assert len(kbs) == 1
        assert kbs[0].id == "test/repo@v1"

# --- Setup Flow Tests ---

@patch("adk_knowledge_ext.manage_mcp.SourceReader")
@patch("adk_knowledge_ext.manage_mcp._configure_ide")
@patch("adk_knowledge_ext.manage_mcp._generate_mcp_config")
@patch("adk_knowledge_ext.manage_mcp._get_existing_kbs_from_configs")
@patch("rich.prompt.Prompt.ask")
@patch("rich.prompt.Confirm.ask")
def test_setup_merge_flow(mock_confirm, mock_ask, mock_get_existing, mock_gen_config, mock_conf_ide, mock_reader, runner):
    # Setup mocks
    mock_get_existing.return_value = [KBDefinition(id="existing/repo@v1", repo_url="url1", version="v1")]
    
    # Mock Confirm.ask to return True for "Configure {ide_name}?" and "Proceed?"
    # But we also have "Do you have a Gemini API Key?" which defaults to False.
    # We'll set env var for API Key to avoid that prompt.
    mock_confirm.return_value = True 
    
    # Mock Prompt.ask for the merge question
    mock_ask.side_effect = lambda prompt, **kwargs: "y" if "Merge" in prompt else "default"

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        result = runner.invoke(manage_mcp.setup, ["--repo-url", "https://github.com/new/repo.git", "--version", "v2"])
    
    if result.exit_code != 0:
        print(result.output)
        
    assert result.exit_code == 0
    
    # Verify logic
    # _generate_mcp_config should be called with merged list
    assert mock_gen_config.called
    call_args = mock_gen_config.call_args
    selected_kbs = call_args[0][0] # First arg
    
    ids = [kb.id for kb in selected_kbs]
    assert "existing/repo@v1" in ids
    assert "custom/repo@v2" in ids

@patch("adk_knowledge_ext.manage_mcp.SourceReader")
@patch("adk_knowledge_ext.manage_mcp._configure_ide")
@patch("adk_knowledge_ext.manage_mcp._generate_mcp_config")
@patch("adk_knowledge_ext.manage_mcp._get_existing_kbs_from_configs")
@patch("rich.prompt.Prompt.ask")
@patch("rich.prompt.Confirm.ask")
def test_setup_replace_flow(mock_confirm, mock_ask, mock_get_existing, mock_gen_config, mock_conf_ide, mock_reader, runner):
    # Setup mocks
    mock_get_existing.return_value = [KBDefinition(id="existing/repo@v1", repo_url="url1", version="v1")]
    mock_confirm.return_value = True
    
    # User says "n" to merge
    mock_ask.side_effect = lambda prompt, **kwargs: "n" if "Merge" in prompt else "default"

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        result = runner.invoke(manage_mcp.setup, ["--repo-url", "https://github.com/new/repo.git", "--version", "v2"])
    
    assert result.exit_code == 0
    
    # Verify logic
    assert mock_gen_config.called
    selected_kbs = mock_gen_config.call_args[0][0]
    
    ids = [kb.id for kb in selected_kbs]
    assert "existing/repo@v1" not in ids
    assert "custom/repo@v2" in ids

@patch("adk_knowledge_ext.manage_mcp.SourceReader")
@patch("adk_knowledge_ext.manage_mcp._configure_ide")
@patch("adk_knowledge_ext.manage_mcp._generate_mcp_config")
@patch("adk_knowledge_ext.manage_mcp._get_existing_kbs_from_configs")
def test_setup_force_skips_merge(mock_get_existing, mock_gen_config, mock_conf_ide, mock_reader, runner):
    # Force=True should skip _get_existing_kbs_from_configs call or at least ignore it
    mock_get_existing.return_value = [KBDefinition(id="existing/repo@v1", repo_url="url1", version="v1")]
    
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        result = runner.invoke(manage_mcp.setup, ["--repo-url", "https://github.com/new/repo.git", "--version", "v2", "--force"])
    
    assert result.exit_code == 0
    
    # Verify we did NOT merge
    selected_kbs = mock_gen_config.call_args[0][0]
    ids = [kb.id for kb in selected_kbs]
    assert "existing/repo@v1" not in ids
    assert "custom/repo@v2" in ids

@patch("rich.prompt.Confirm.ask")
def test_ask_confirm_case_insensitive(mock_confirm_ask):
    """Ensure ask_confirm is case-insensitive."""
    mock_confirm_ask.return_value = True
    
    manage_mcp.ask_confirm("Question?")
    
    mock_confirm_ask.assert_called_once_with("Question?", default=True, case_sensitive=False)

# --- Remove Command Tests ---

@patch("adk_knowledge_ext.manage_mcp._remove_mcp_config")
@patch("adk_knowledge_ext.manage_mcp.ask_confirm")
@patch("shutil.which")
def test_remove_interactive(mock_which, mock_confirm, mock_remove, runner):
    """
    Scenario: Interactive Removal (Default)
    
    Verifies that running `remove` without flags:
    1. Detects configured IDEs.
    2. Prompts the user for confirmation for each IDE.
    3. Calls the removal logic if confirmed.
    4. Displays status messages.
    """
    mock_which.return_value = "/bin/fake-ide"  # Assume IDE is runnable
    mock_confirm.return_value = True # Confirm removal
    
    # Mock IDE detection
    mock_ide_info = MagicMock()
    mock_ide_info.detect_path.exists.return_value = True
    mock_ide_info.config_method = "json"
    
    # Mock _is_mcp_configured to return True
    with (
        patch("adk_knowledge_ext.manage_mcp._is_mcp_configured", return_value=True), 
        patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {"TestIDE": mock_ide_info})
    ):
        
        result = runner.invoke(manage_mcp.remove)
        
        assert result.exit_code == 0
        assert "Remove from:" in result.output
        assert mock_confirm.called
        assert mock_remove.called

@patch("adk_knowledge_ext.manage_mcp._remove_mcp_config")
@patch("adk_knowledge_ext.manage_mcp.ask_confirm")
@patch("shutil.which")
def test_remove_quiet(mock_which, mock_confirm, mock_remove, runner):
    """
    Scenario: Quiet Removal (`--quiet`)
    
    Verifies that `remove --quiet`:
    1. Skips confirmation prompts (implicit force).
    2. Suppresses ALL standard output (stdout).
    3. Executes the removal logic silently.
    """
    mock_which.return_value = "/bin/fake-ide"
    
    mock_ide_info = MagicMock()
    mock_ide_info.detect_path.exists.return_value = True
    mock_ide_info.config_method = "json"
    
    with (
        patch("adk_knowledge_ext.manage_mcp._is_mcp_configured", return_value=True), 
        patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {"TestIDE": mock_ide_info})
    ):
        
        result = runner.invoke(manage_mcp.remove, ["--quiet"])
        
        assert result.exit_code == 0
        assert result.output == "" # Should be absolutely silent
        assert not mock_confirm.called # Should NOT ask for confirmation
        assert mock_remove.called # Should still perform the action

# --- Debug Command Tests ---

@pytest.fixture
def mock_mcp_client():
    """Mocks the MCP client context managers and session."""
    with (
        patch("adk_knowledge_ext.manage_mcp.stdio_client") as mock_stdio,
        patch("adk_knowledge_ext.manage_mcp.ClientSession") as mock_session_cls
    ):
        
        # Setup the async context manager for stdio_client
        mock_read = MagicMock()
        mock_write = MagicMock()
        mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
        mock_stdio.return_value.__aexit__.return_value = None
        
        # Setup the async context manager for ClientSession
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_session_cls.return_value.__aexit__.return_value = None
        
        yield mock_session

def create_tool_result(text, is_error=False):
    """Helper to create a mock tool result object."""
    content_obj = MagicMock()
    content_obj.text = text
    result = MagicMock()
    result.content = [content_obj]
    result.isError = is_error
    return result

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

@patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {})
def test_debug_inspect_symbol_success_with_error_word(mock_mcp_client, runner):
    """
    Scenario: Success with "False Positive" Text
    Verifies that inspect_symbol is marked as OK even if the returned docstring 
    contains the word "Error" or "not found", provided it doesn't match a failure pattern.
    This prevents false positives when documentation describes error conditions.
    """
    # 1. List Tools (Success)
    t1 = MagicMock(); t1.name = "list_modules"
    t2 = MagicMock(); t2.name = "search_knowledge"
    t3 = MagicMock(); t3.name = "inspect_symbol"
    
    tools_result = MagicMock()
    tools_result.tools = [t1, t2, t3]
    mock_mcp_client.list_tools.return_value = tools_result
    
    # 2. Mock responses for the sequence of calls
    
    docstring_with_error = ""+\
    "    rank: 1\n"+\
    "    id: google.adk.runners.InMemoryRunner\n"+\
    "    docstring: \"Raises: ValueError: If the session is not found.\"\n"+\
    "    "
    
    mock_mcp_client.call_tool.side_effect = [
        create_tool_result("[1] CLASS: google.adk.runners.InMemoryRunner"), # list_modules
        create_tool_result("Found some stuff"), # search_knowledge (keyword)
        create_tool_result("Vector Search Result"), # search_knowledge (vector check)
        create_tool_result(docstring_with_error) # inspect_symbol
    ]
    
    result = runner.invoke(manage_mcp.debug)
    clean_output = strip_ansi(result.output)
    
    # We expect "inspect_symbol" to NOT show "Failed"
    # It should show "OK"
    assert "✅ OK" in clean_output
    # Specifically for the inspect step
    # We can check that we don't see "Output (Error)" which is printed on failure
    assert "Output (Error)" not in clean_output

@patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {})
def test_debug_inspect_symbol_real_failure(mock_mcp_client, runner):
    """
    Scenario: Logical Failure ("Symbol Not Found")
    """
    t1 = MagicMock(); t1.name = "list_modules"
    t2 = MagicMock(); t2.name = "search_knowledge"
    t3 = MagicMock(); t3.name = "inspect_symbol"
    
    tools_result = MagicMock()
    tools_result.tools = [t1, t2, t3]
    mock_mcp_client.list_tools.return_value = tools_result
    
    mock_mcp_client.call_tool.side_effect = [
        create_tool_result("[1] CLASS: google.adk.runners.InMemoryRunner"), 
        create_tool_result("Found stuff"), 
        create_tool_result("Vector check"),
        create_tool_result("Symbol 'google.adk.runners.InMemoryRunner' not found in index.") 
    ]
    
    result = runner.invoke(manage_mcp.debug)
    clean_output = strip_ansi(result.output)
    
    assert "❌ Failed" in clean_output
    assert "Output (Error)" in clean_output

@patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {})
def test_debug_inspect_symbol_generic_error(mock_mcp_client, runner):
    """Scenario: Explicit Error Prefix"""
    t1 = MagicMock(); t1.name = "list_modules"
    t2 = MagicMock(); t2.name = "search_knowledge"
    t3 = MagicMock(); t3.name = "inspect_symbol"
    
    tools_result = MagicMock()
    tools_result.tools = [t1, t2, t3]
    mock_mcp_client.list_tools.return_value = tools_result
    
    mock_mcp_client.call_tool.side_effect = [
        create_tool_result("[1] CLASS: google.adk.runners.InMemoryRunner"), 
        create_tool_result("Found stuff"), 
        create_tool_result("Vector check"),
        create_tool_result("Error: Something went wrong.") 
    ]
    
    result = runner.invoke(manage_mcp.debug)
    clean_output = strip_ansi(result.output)
    
    assert "❌ Failed" in clean_output
    assert "Output (Error)" in clean_output

@patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {})
def test_debug_inspect_symbol_is_error(mock_mcp_client, runner):
    """Scenario: Protocol-Level Error (isError=True)"""
    t1 = MagicMock(); t1.name = "list_modules"
    t2 = MagicMock(); t2.name = "search_knowledge"
    t3 = MagicMock(); t3.name = "inspect_symbol"
    
    tools_result = MagicMock()
    tools_result.tools = [t1, t2, t3]
    mock_mcp_client.list_tools.return_value = tools_result
    
    mock_mcp_client.call_tool.side_effect = [
        create_tool_result("[1] CLASS: google.adk.runners.InMemoryRunner"), 
        create_tool_result("Found stuff"), 
        create_tool_result("Vector check"),
        create_tool_result("Some unexpected error occurred internally", is_error=True) 
    ]
    
    result = runner.invoke(manage_mcp.debug)
    clean_output = strip_ansi(result.output)
    
    assert "❌ Failed" in clean_output
    assert "Output (Error)" in clean_output


# --- Debug Edge Cases (Mocked Integration) ---

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
    
    # We need to make sure we use the correct src path even in this helper if it re-imports or similar
    # But since we imported manage_mcp already, it should be fine.
    
    with (
        patch.dict(manage_mcp.IDE_CONFIGS, {"TestIDE": mock_ide_config}, clear=True),
        patch("adk_knowledge_ext.manage_mcp._is_mcp_configured", return_value=True),
    ):
        import os
        from pathlib import Path
        env = os.environ.copy()
        pkg_src = str(Path(__file__).parents[3] / "src")
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{pkg_src}:{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = pkg_src
        
        result = runner.invoke(manage_mcp.debug, env=env)
        
    return strip_ansi(result.output)

def test_edge_case_symbol_field_collision(create_test_env, runner):
    """
    Scenario: 'Symbol' Field Collision (False Positive Check)
    """
    data = [{
        "rank": 1,
        "id": "test.Collision",
        "name": "Collision",
        "type": "CLASS",
        "Symbol": "This string contains not found", 
        "file_path": "src/test.py"
    }]
    
    config_path, _ = create_test_env(data)
    output = run_debug_with_env(runner, config_path)
    
    assert "inspect_symbol" in output
    assert "test.Collision" in output
    assert "✅ OK" in output

def test_edge_case_error_prefix_in_docstring(create_test_env, runner):
    """
    Scenario: 'Error:' Prefix in Docstring (False Positive Check)
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
