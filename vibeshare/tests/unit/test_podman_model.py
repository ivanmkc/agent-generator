import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from models.podman_model import PodmanModel

@pytest.mark.asyncio
async def test_podman_model_initialization():
    """Test that PodmanModel initializes with correct attributes."""
    with patch("models.podman_model.PodmanContainer") as MockContainer:
        model = PodmanModel(model_name="gemini/test", image_name="test-image")
        assert model.model_name == "gemini/test"
        MockContainer.assert_called_with(image_name="test-image")

@pytest.mark.asyncio
async def test_podman_model_predict_success():
    """Test successful prediction."""
    with patch("models.podman_model.PodmanContainer") as MockContainer:
        mock_instance = MockContainer.return_value
        # Mock send_command response
        mock_instance.send_command = AsyncMock(return_value={
            "stdout": "Response text",
            "stderr": "",
            "returncode": 0
        })
        
        model = PodmanModel(model_name="gemini/test", image_name="test-image")
        response = await model.predict("Hello")
        
        assert response == "Response text"
        mock_instance.send_command.assert_called_once()
        args, kwargs = mock_instance.send_command.call_args
        assert args[0] == ["gemini", "Hello"]
        assert args[1] == {}  # Empty env

@pytest.mark.asyncio
async def test_podman_model_predict_failure():
    """Test prediction failure (non-zero return code)."""
    with patch("models.podman_model.PodmanContainer") as MockContainer:
        mock_instance = MockContainer.return_value
        mock_instance.send_command = AsyncMock(return_value={
            "stdout": "",
            "stderr": "Error happened",
            "returncode": 1
        })
        
        model = PodmanModel(model_name="gemini/test", image_name="test-image")
        
        with pytest.raises(RuntimeError, match="Gemini CLI failed"):
            await model.predict("Hello")

