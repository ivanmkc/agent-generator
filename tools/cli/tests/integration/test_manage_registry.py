"""
Tests for the `manage_registry` CLI tool.

Verifies the functionality of registry management commands, including:
- Checking for updates (comparing local vs remote tags)
- Interactive update selection
- Processing version updates (installation/ranking/embeddings)
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from click.testing import CliRunner
from tools.cli import manage_registry

@pytest.fixture
def runner():
    return CliRunner()

@patch("tools.cli.manage_registry.get_remote_tags")
def test_find_available_updates(mock_get_tags):
    """
    Tests that `find_available_updates` correctly compares remote tags against installed versions 
    to identify available updates.
    
    Expectations:
    - Returns a dictionary mapping repo URLs to lists of new version tags.
    - Correctly identifies "v1.1.0" as an update for "repo/a".
    - Correctly identifies "repo/b" as up-to-date.
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
def test_check_updates_command(mock_find, mock_load, runner):
    """
    Tests that the `check-updates` CLI command correctly invokes `find_available_updates` 
    and outputs the results.
    
    Expectations:
    - Command exits with 0 (success).
    - Output contains the repository ID ("repo/a").
    - Output contains the available version ("v1.1.0").
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
def test_update_interactive_all(mock_checkbox, mock_load, mock_find, mock_process, runner):
    """
    Tests the `update` command interactively when the user selects multiple updates.
    
    Expectations:
    - `questionary.checkbox` is used to prompt the user.
    - `process_version_update` is called for each selected repository/version (repo/a and repo/b).
    """
    # Setup
    mock_registry = manage_registry.Registry(repositories={
        "repo/a": manage_registry.Repository(repo_url="url1", versions={}),
        "repo/b": manage_registry.Repository(repo_url="url2", versions={})
    })
    mock_load.return_value = mock_registry
    mock_find.return_value = {
        "repo/a": ["v1.1.0"],
        "repo/b": ["v2.0.0"]
    }
    
    # User selects "all" (indices 0 and 1)
    mock_ask = MagicMock()
    mock_ask.ask.return_value = [0, 1]
    mock_checkbox.return_value = mock_ask
    
    result = runner.invoke(manage_registry.update)
    
    assert result.exit_code == 0
    assert mock_process.call_count == 2
    calls = mock_process.call_args_list
    repo_ids = {c[0][0] for c in calls}
    assert "repo/a" in repo_ids
    assert "repo/b" in repo_ids

@patch("tools.cli.manage_registry.process_version_update")
@patch("tools.cli.manage_registry.find_available_updates")
@patch("tools.cli.manage_registry.load_registry")
@patch("tools.cli.manage_registry.questionary.checkbox")
def test_update_interactive_select_index(mock_checkbox, mock_load, mock_find, mock_process, runner):
    """
    Tests the `update` command when the user selects a specific update from the list.
    
    Expectations:
    - User selects index 1 (v1.2.0 for repo/a).
    - `process_version_update` is called *only* for the selected version (v1.2.0).
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
    mock_process.assert_called_with("repo/a", "v1.2.0", force=False, registry=mock_registry)

@patch("tools.cli.manage_registry.process_version_update")
@patch("tools.cli.manage_registry.find_available_updates")
@patch("tools.cli.manage_registry.load_registry")
@patch("tools.cli.manage_registry.questionary.checkbox")
def test_update_interactive_none(mock_checkbox, mock_load, mock_find, mock_process, runner):
    """
    Tests the `update` command when the user cancels the selection (returns None).
    
    Expectations:
    - `questionary.checkbox` returns None.
    - `process_version_update` is NOT called.
    - Command exits gracefully with 0.
    """
    mock_registry = manage_registry.Registry(repositories={
        "repo/a": manage_registry.Repository(repo_url="url1", versions={})
    })
    mock_load.return_value = mock_registry
    mock_find.return_value = {"repo/a": ["v1.1.0"]}
    
    # User cancels (returns None)
    mock_ask = MagicMock()
    mock_ask.ask.return_value = None
    mock_checkbox.return_value = mock_ask
    
    result = runner.invoke(manage_registry.update)
    
    assert result.exit_code == 0
    mock_process.assert_not_called()

@pytest.mark.asyncio
@patch("tools.cli.manage_registry.save_registry")
@patch("tools.cli.manage_registry.load_registry")
@patch("tools.cli.manage_registry.TargetRanker")
@patch("tools.cli.manage_registry.build_index")
@patch("tools.cli.manage_registry.generate_cooccurrence")
@patch("tools.cli.manage_registry.shutil.rmtree")
@patch("tools.cli.manage_registry.subprocess.run")
@patch("tools.cli.manage_registry.Path.mkdir")
@patch("tools.cli.manage_registry.Path.exists")
async def test_process_version_update_adds_version(
    mock_exists, mock_mkdir, mock_run, mock_rmtree, mock_cooccurrence, mock_build, mock_ranker, mock_load, mock_save
):
    """
    Tests that `process_version_update` correctly adds new versions to the registry.
    
    Expectations:
    - Installing a newer version (v1.1.0) adds it to the registry.
    - Installing an older version (v0.9.0) adds it to the registry.
    """
    # Setup
    repo_id = "repo/a"
    mock_registry = manage_registry.Registry(repositories={
        repo_id: manage_registry.Repository(
            repo_url="url1", 
            versions={"v1.0.0": manage_registry.VersionInfo(index_url="path")}
        )
    })
    mock_load.return_value = mock_registry
    mock_exists.return_value = False # tmp_dir does not exist
    
    # Mock Ranker
    mock_ranker_instance = MagicMock()
    mock_ranker_instance.generate = AsyncMock()
    mock_ranker.return_value = mock_ranker_instance
    
    # Act: Add a newer version
    await manage_registry.process_version_update(repo_id, "v1.1.0", force=False, registry=mock_registry)
    
    # Assert
    assert "v1.1.0" in mock_registry.repositories[repo_id].versions
    
    # Act: Add an older version
    await manage_registry.process_version_update(repo_id, "v0.9.0", force=False, registry=mock_registry)
    
    # Assert
    assert "v0.9.0" in mock_registry.repositories[repo_id].versions
