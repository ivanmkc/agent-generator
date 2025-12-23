import pytest
import shutil
import tempfile
from pathlib import Path
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator

class TestWorkflowAdkAgent:
    @pytest.fixture
    def workspace(self):
        tmp_dir = Path(tempfile.mkdtemp()).resolve()
        yield tmp_dir
        shutil.rmtree(tmp_dir)

    @pytest.fixture
    def generator(self, workspace):
        return AdkAnswerGenerator(enable_workflow=True, workspace_root=workspace)

    def test_resolve_path_safe(self, generator, workspace):
        """Test resolving safe paths within the workspace."""
        # Relative path
        p1 = generator.tools._resolve_path("test.txt")
        assert p1 == workspace / "test.txt"

        # Path in subdirectory
        p2 = generator.tools._resolve_path("subdir/test.txt")
        assert p2 == workspace / "subdir" / "test.txt"

        # Explicit relative path
        p3 = generator.tools._resolve_path("./test.txt")
        assert p3 == workspace / "test.txt"

    def test_resolve_path_unsafe(self, generator, workspace):
        """Test that unsafe paths raise ValueError."""
        # Parent directory traversal
        with pytest.raises(ValueError, match="outside the workspace"):
            generator.tools._resolve_path("../outside.txt")

        # Absolute path outside workspace
        with pytest.raises(ValueError, match="outside the workspace"):
            generator.tools._resolve_path("/etc/passwd")
            
        # Tricky traversal
        with pytest.raises(ValueError, match="outside the workspace"):
            generator.tools._resolve_path("subdir/../../outside.txt")

    def test_file_operations(self, generator, workspace):
        """Test read and write operations."""
        # Write
        result = generator.tools.write_file("test.txt", "Hello World")
        assert "Successfully wrote" in result
        assert (workspace / "test.txt").read_text() == "Hello World"

        # Read
        content = generator.tools.read_file("test.txt")
        assert content == "Hello World"

        # List
        listing = generator.tools.list_directory(".")
        assert "test.txt" in listing

    def test_shell_execution_cwd(self, generator, workspace):
        """Test that shell commands run in the workspace."""
        # Check CWD
        result = generator.tools.run_shell_command("pwd")
        assert str(workspace) in result
