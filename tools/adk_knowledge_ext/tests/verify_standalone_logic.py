import sys
import os
import importlib.util
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path

# --- Mocking Infrastructure ---

# Mock Click to handle decorators without altering functions
mock_click = MagicMock()

# This is the DECORATOR returned by the factory
def identity_decorator(f):
    return f

def group_decorator(*args, **kwargs):
    def wrapper(f):
        # Return a mock that has .command() method returning a decorator
        group_mock = MagicMock()
        # When group_mock.command() is called, it returns identity_decorator
        group_mock.command.return_value = identity_decorator
        return group_mock
    # Usually group() is called as factory, so it returns wrapper
    return wrapper

# When click.group() is called, it returns wrapper (the decorator)
mock_click.group.side_effect = group_decorator

# For simple decorators like @click.argument("name")
# calling click.argument(...) returns the decorator
mock_click.command.return_value = identity_decorator
mock_click.argument.return_value = identity_decorator
mock_click.option.return_value = identity_decorator
sys.modules["click"] = mock_click

# Mock Rich
mock_rich = MagicMock()
sys.modules["rich"] = mock_rich
sys.modules["rich.console"] = MagicMock()
sys.modules["rich.table"] = MagicMock()
sys.modules["rich.prompt"] = MagicMock()

# --- Import Target Module ---
PROJECT_ROOT = Path(__file__).parents[3]
TOOLS_DIR = PROJECT_ROOT / "tools"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

# Import manage_registry by path
spec = importlib.util.spec_from_file_location("manage_registry", TOOLS_DIR / "manage_registry.py")
manage_registry = importlib.util.module_from_spec(spec)
sys.modules["manage_registry"] = manage_registry
spec.loader.exec_module(manage_registry)

# Extract Classes
Registry = manage_registry.Registry
Repository = manage_registry.Repository
VersionInfo = manage_registry.VersionInfo

# --- Tests ---

def test_find_available_updates():
    print("Running test_find_available_updates...", end=" ")
    
    repos = {
        "repo/a": Repository(
            repo_url="url1", 
            versions={"v1.0.0": VersionInfo(index_url="path/to/index")}
        ),
        "repo/b": Repository(
            repo_url="url2", 
            versions={"v1.0.0": VersionInfo(index_url="path/to/index")}
        )
    }
    
    with patch("manage_registry.get_remote_tags") as mock_get_tags:
        # repo/a has update, repo/b is up to date
        mock_get_tags.side_effect = lambda url: ["v1.1.0", "v1.0.0"] if url == "url1" else ["v1.0.0"]
        
        updates = manage_registry.find_available_updates(repos)
        
        assert "repo/a" in updates, "repo/a should have updates"
        assert "v1.1.0" in updates["repo/a"], "repo/a should have v1.1.0"
        assert "v1.0.0" in updates["repo/a"], "repo/a should have v1.0.0 (installed)"
        
        # New behavior: repo/b IS in updates because it has valid tags, even if installed
        assert "repo/b" in updates, "repo/b should be in updates (for re-install option)"
        assert "v1.0.0" in updates["repo/b"]
    print("PASS")

def test_check_updates_logic():
    print("Running test_check_updates_logic...", end=" ")
    
    # Verify it calls find_available_updates and mocks internal loading
    with patch("manage_registry.load_registry") as mock_load, \
         patch("manage_registry.find_available_updates") as mock_find, \
         patch("manage_registry.console") as mock_console:
        
        # Mock load_registry returning a Registry object
        mock_registry = Registry(
            repositories={
                "repo/a": Repository(
                    repo_url="url1",
                    versions={"v1.0.0": VersionInfo(index_url="path")}
                )
            }
        )
        mock_load.return_value = mock_registry
        
        mock_find.return_value = {"repo/a": ["v1.1.0"]}
        
        # Call the command function directly
        manage_registry.check_updates()
        
        assert mock_find.call_count == 1, "Should call find_available_updates"
        mock_find.assert_called_with(mock_registry.repositories)
        assert mock_console.print.called, "Should print table"
        
    print("PASS")

def test_update_interactive_selection():
    print("Running test_update_interactive_selection...", end=" ")
    
    with patch("manage_registry.load_registry") as mock_load, \
         patch("manage_registry.find_available_updates") as mock_find, \
         patch("manage_registry.process_version_update") as mock_process, \
         patch("rich.prompt.Prompt.ask") as mock_ask:
         
        # Fix: Registry must contain the repo to avoid logic failure
        mock_registry = Registry(repositories={
            "repo/a": Repository(repo_url="urlA", versions={})
        })
        mock_load.return_value = mock_registry
        mock_find.return_value = {"repo/a": ["v1.1.0"]}
        
        # User selects "all"
        mock_ask.return_value = "all"
        
        manage_registry.update()
        
        # force=False because repo/a doesn't have v1.1.0 installed in mock
        mock_process.assert_called_with("repo/a", "v1.1.0", force=False, golden=[], registry=mock_registry)
        
    print("PASS")

def test_process_version_update_calls_scripts():
    print("Running test_process_version_update_calls_scripts...", end=" ")
    
    with patch("manage_registry.subprocess.run") as mock_run, \
         patch("manage_registry.shutil.rmtree") as mock_rm, \
         patch("manage_registry.Path.mkdir") as mock_mkdir, \
         patch("manage_registry.save_registry") as mock_save, \
         patch("manage_registry.console.print"):
         
        # Mock file operations for validation
        with patch("manage_registry.open"), patch("manage_registry.yaml.safe_load") as mock_yaml_load:
            mock_yaml_load.return_value = [] # Mock empty index for validation pass
            
            repo = Repository(repo_url="https://github.com/test/repo", versions={})
            registry = Registry(repositories={"test/repo": repo})
            
            manage_registry.process_version_update(
                "test/repo", 
                "v1.0.0", 
                force=False, 
                golden=[], 
                registry=registry
            )
            
            # Verify git clone
            assert any("git" in str(call) for call in mock_run.call_args_list), "Should call git clone"
            
            # Verify ranker script call
            assert any("run_ranker.py" in str(call) for call in mock_run.call_args_list), "Should call run_ranker.py"
            
            # Verify embedding script call
            assert any("build_vector_index.py" in str(call) for call in mock_run.call_args_list), "Should call build_vector_index.py"
            
            # Verify registry update
            assert "v1.0.0" in repo.versions
            mock_save.assert_called()

    print("PASS")

if __name__ == "__main__":
    try:
        test_find_available_updates()
        test_check_updates_logic()
        test_update_interactive_selection()
        test_process_version_update_calls_scripts()
        print("\nAll standalone tests passed!")
    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
