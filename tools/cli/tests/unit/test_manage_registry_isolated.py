
import sys
from unittest.mock import MagicMock

# Mock numpy and build_vector_index before ANY other locally imported modules
sys.modules["tools.knowledge.build_vector_index"] = MagicMock()

import pytest
from unittest.mock import patch, AsyncMock
from click.testing import CliRunner
from tools.cli import manage_registry

@pytest.fixture
def runner():
    return CliRunner()

@patch("tools.cli.manage_registry.get_remote_tags")
def test_find_available_updates_isolated(mock_get_tags):
    """
    Tests that `find_available_updates` correctly compares remote tags against installed versions 
    to identify available updates.
    """
    # Setup
    repos = {
        "repo/a": manage_registry.Repository(
            repo_url="url1", 
            versions={"v1.0.0": manage_registry.VersionInfo(index_url="path")}
        ),
        "repo/b": manage_registry.Repository(
            repo_url="url2", 
            versions={"v1.0.0": manage_registry.VersionInfo(index_url="path")}
        )
    }
    
    # repo/a has update, repo/b is up to date
    mock_get_tags.side_effect = lambda url: ["v1.1.0", "v1.0.0"] if url == "url1" else ["v1.0.0"]
    
    updates = manage_registry.find_available_updates(repos)
    
    assert "repo/a" in updates
    assert updates["repo/a"] == ["v1.1.0", "v1.0.0"]
    assert "repo/b" in updates
    assert updates["repo/b"] == ["v1.0.0"]

@patch("tools.cli.manage_registry.load_registry")
@patch("tools.cli.manage_registry.find_available_updates")
def test_check_updates_command_isolated(mock_find, mock_load, runner):
    """
    Tests that the `check-updates` CLI command correctly invokes `find_available_updates` 
    and outputs the results.
    """
    mock_registry = manage_registry.Registry(
        repositories={
            "repo/a": manage_registry.Repository(
                repo_url="url1",
                versions={"v1.0.0": manage_registry.VersionInfo(index_url="path")}
            )
        }
    )
    mock_load.return_value = mock_registry
    mock_find.return_value = {"repo/a": ["v1.1.0"]}
    
    result = runner.invoke(manage_registry.check_updates)
    
    assert result.exit_code == 0
    assert "repo/a" in result.output
    assert "v1.1.0" in result.output

@patch("tools.cli.manage_registry.process_version_update")
@patch("tools.cli.manage_registry.find_available_updates")
@patch("tools.cli.manage_registry.load_registry")
@patch("tools.cli.manage_registry.questionary.checkbox")
def test_update_interactive_select_index_isolated(mock_checkbox, mock_load, mock_find, mock_process, runner):
    """
    Tests the `update` command when the user selects a specific update from the list.
    """
    # Setup
    mock_registry = manage_registry.Registry(repositories={
        "repo/a": manage_registry.Repository(repo_url="url1", versions={})
    })
    mock_load.return_value = mock_registry
    mock_find.return_value = {"repo/a": ["v1.1.0", "v1.2.0"]}
    
    # User selects index 1 (v1.2.0)
    mock_ask = MagicMock()
    mock_ask.ask.return_value = [1]
    mock_checkbox.return_value = mock_ask
    
    result = runner.invoke(manage_registry.update)
    
    assert result.exit_code == 0
    assert mock_process.call_count == 1
    # Verify strict call arguments
    mock_process.assert_called_with("repo/a", "v1.2.0", force=False, registry=mock_registry)
