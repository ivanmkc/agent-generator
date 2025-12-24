import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
from benchmarks.answer_generators.adk_agents import create_workflow_adk_generator
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator

class TestAdkAgents:

    @pytest.mark.asyncio
    async def test_create_workflow_adk_generator_setup(self):
        """Test the setup_hook logic of the workflow generator."""
        
        mock_workspace = Path("/tmp/mock_workspace")
        mock_venv = mock_workspace / "venv"
        mock_repo = mock_workspace / "repos" / "adk-python"

        with patch("benchmarks.answer_generators.adk_agents.tempfile.mkdtemp", return_value=str(mock_workspace)), \
             patch("benchmarks.answer_generators.adk_agents.subprocess.run") as mock_run, \
             patch("pathlib.Path.mkdir") as mock_mkdir, \
             patch("pathlib.Path.exists") as mock_exists, \
             patch("shutil.rmtree") as mock_rmtree:

            # Setup mocks
            # Simulate paths NOT existing initially to trigger all setup steps
            mock_exists.side_effect = lambda: False 
            
            # Create generator
            generator = create_workflow_adk_generator(model_name="test-model")
            
            assert isinstance(generator, AdkAnswerGenerator)
            assert generator.agent.name == "workflow_solver"
            
            # Run setup hook
            await generator.setup()
            
            # Verify Setup Actions
            
            # 1. Directory Creation
            # We expect mkdir calls for workspace and repos
            assert mock_mkdir.call_count >= 1
            
            # 2. Git Clone
            expected_clone_cmd = [
                "git", "clone", "--branch", "v1.20.0", 
                "https://github.com/google/adk-python.git", str(mock_repo)
            ]
            mock_run.assert_any_call(expected_clone_cmd, check=True, capture_output=True)
            
            # 3. Venv Creation
            # os.sys.executable is needed for venv call
            import os
            expected_venv_cmd = [os.sys.executable, "-m", "venv", str(mock_venv)]
            mock_run.assert_any_call(expected_venv_cmd, check=True)
            
            # 4. Pip Installs
            pip_path = str(mock_venv / "bin" / "pip")
            
            # Upgrade pip
            mock_run.assert_any_call([pip_path, "install", "--upgrade", "pip"], check=True)
            
            # Install deps
            mock_run.assert_any_call([pip_path, "install", "pytest", "google-adk"], check=True)
            
            # Install local repo
            mock_run.assert_any_call([pip_path, "install", "-e", str(mock_repo)], check=True)

    @pytest.mark.asyncio
    async def test_create_workflow_adk_generator_teardown(self):
        """Test the teardown_hook logic."""
        mock_workspace = Path("/tmp/mock_adk_workflow_123")
        
        with patch("benchmarks.answer_generators.adk_agents.tempfile.mkdtemp", return_value=str(mock_workspace)), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("shutil.rmtree") as mock_rmtree:
             
            generator = create_workflow_adk_generator(model_name="test-model")
            
            await generator.teardown()
            
            # Should delete because path contains "adk_workflow_"
            mock_rmtree.assert_called_with(mock_workspace)

    @pytest.mark.asyncio
    async def test_create_workflow_adk_generator_teardown_safety(self):
        """Test teardown safety check."""
        # Path NOT containing "adk_workflow_"
        mock_workspace = Path("/tmp/my_important_files")
        
        with patch("benchmarks.answer_generators.adk_agents.tempfile.mkdtemp", return_value=str(mock_workspace)), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("shutil.rmtree") as mock_rmtree:
             
            generator = create_workflow_adk_generator(model_name="test-model")
            
            await generator.teardown()
            
            # Should NOT delete
            mock_rmtree.assert_not_called()
