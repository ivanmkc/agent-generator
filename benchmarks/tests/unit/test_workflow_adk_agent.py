import pytest
import shutil
import tempfile
from pathlib import Path
from benchmarks.answer_generators.adk_tools import AdkTools

class TestAdkTools:
    @pytest.fixture
    def workspace(self):
        tmp_dir = Path(tempfile.mkdtemp()).resolve()
        yield tmp_dir
        shutil.rmtree(tmp_dir)

    @pytest.fixture
    def tools(self, workspace):
        return AdkTools(workspace_root=workspace)

    def test_resolve_path_safe(self, tools, workspace):
        """Test resolving safe paths within the workspace."""
        # Relative path
        p1 = tools._resolve_path("test.txt")
        assert p1 == workspace / "test.txt"

        # Path in subdirectory
        p2 = tools._resolve_path("subdir/test.txt")
        assert p2 == workspace / "subdir" / "test.txt"

        # Explicit relative path
        p3 = tools._resolve_path("./test.txt")
        assert p3 == workspace / "test.txt"

    def test_resolve_path_unsafe(self, tools, workspace):
        """Test that unsafe paths raise ValueError."""
        # Parent directory traversal
        with pytest.raises(ValueError, match="outside the workspace"):
            tools._resolve_path("../outside.txt")

        # Absolute path outside workspace
        with pytest.raises(ValueError, match="outside the workspace"):
            tools._resolve_path("/etc/passwd")
            
        # Tricky traversal
        with pytest.raises(ValueError, match="outside the workspace"):
            tools._resolve_path("subdir/../../outside.txt")

    def test_file_operations(self, tools, workspace):
        """Test read and write operations."""
        # Write
        result = tools.write_file("test.txt", "Hello World")
        assert "Successfully wrote" in result
        assert (workspace / "test.txt").read_text() == "Hello World"

        # Read
        content = tools.read_file("test.txt")
        assert content == "Hello World"

        # List
        listing = tools.list_directory(".")
        assert "test.txt" in listing

    def test_shell_execution_cwd(self, tools, workspace):
        """Test that shell commands run in the workspace."""
        # Check CWD
        result = tools.run_shell_command("pwd")
        assert str(workspace) in result
