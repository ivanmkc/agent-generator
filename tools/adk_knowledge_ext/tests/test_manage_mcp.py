import pytest
from unittest.mock import MagicMock, patch, mock_open
from click.testing import CliRunner
import json
import os
from pathlib import Path

# Import the module
# We need to make sure the import works given the structure
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from adk_knowledge_ext import manage_mcp
from adk_knowledge_ext.manage_mcp import KBDefinition

@pytest.fixture
def runner():
    return CliRunner()

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
