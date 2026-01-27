"""Test Podman Integration module."""

import pytest
import shutil
import asyncio
from models.podman_model import PodmanModel

# Check if podman is installed
PODMAN_AVAILABLE = shutil.which("podman") is not None


@pytest.mark.asyncio
@pytest.mark.skipif(not PODMAN_AVAILABLE, reason="Podman is not installed")
async def test_podman_integration_lifecycle():
    """
    Integration test for PodmanModel.
    Verifies that we can start a container, run a simple command, and get output.
    Uses 'localhost/gemini-cli:base' which should be present from setup.
    """
    # Use the base image which we know exists from the 'podman images' command earlier
    model = PodmanModel(
        model_name="gemini-cli-podman/base", image_name="localhost/gemini-cli:base"
    )

    try:
        # Check version. This shouldn't require an API key or external network.
        # It executes 'gemini --version' inside the container.
        output = await model.predict("--version")

        print(f"Integration Test Output: {output}")
        assert len(output) > 0
        # The output should look like a version string (e.g. "0.1.0" or similar)
        # We'll just check it's not empty and doesn't contain error keywords usually
        assert "error" not in output.lower()

    finally:
        # Ensure cleanup happens even if test fails
        model._cleanup()
