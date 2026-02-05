"""
Unit tests for the `remove` command in the MCP Management CLI.

This module verifies the behavior of the `mcp-manage remove` command, specifically focusing on:
- Interactive confirmation flows.
- Quiet mode (`--quiet`) for automated scripts.
- Forced mode (`--force`) for skipping confirmations with feedback.
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
from click.testing import CliRunner
import shutil
from pathlib import Path

# Ensure import works
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from adk_knowledge_ext import manage_mcp

@pytest.fixture
def runner():
    return CliRunner()

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
    1. Implies `--force` (no confirmation prompts).
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

@patch("adk_knowledge_ext.manage_mcp._remove_mcp_config")
@patch("adk_knowledge_ext.manage_mcp.ask_confirm")
@patch("shutil.which")
def test_remove_force(mock_which, mock_confirm, mock_remove, runner):
    """
    Scenario: Forced Removal (`--force`)
    
    Verifies that `remove --force`:
    1. Skips confirmation prompts.
    2. Still displays status output (unlike quiet mode).
    3. Executes the removal logic.
    """
    mock_which.return_value = "/bin/fake-ide"
    
    mock_ide_info = MagicMock()
    mock_ide_info.detect_path.exists.return_value = True
    mock_ide_info.config_method = "json"
    
    with (
        patch("adk_knowledge_ext.manage_mcp.IDE_CONFIGS", {"TestIDE": mock_ide_info}),
        patch("adk_knowledge_ext.manage_mcp._is_mcp_configured", return_value=True)
    ):
        
        result = runner.invoke(manage_mcp.remove, ["--force"])
        
        assert result.exit_code == 0
        assert "Codebase Knowledge MCP Remove" in result.output # Should show header
        assert "removed" in result.output # Should show success message
        assert not mock_confirm.called # Should NOT ask
        assert mock_remove.called