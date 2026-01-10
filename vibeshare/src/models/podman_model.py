import asyncio
from typing import Optional, Any
from .model import Model
from benchmarks.answer_generators.gemini_cli_docker.podman_utils import PodmanContainer

class PodmanModel(Model):
    """
    Model implementation that delegates to a Gemini CLI running in a Podman container.
    """

    def __init__(self, model_name: str, image_name: str, **kwargs: Any):
        """
        Initialize the PodmanModel.

        Args:
            model_name (str): The name of the model (e.g., 'gemini/base').
            image_name (str): The Podman image to run (e.g., 'localhost/gemini-cli:base').
            **kwargs: Additional arguments.
        """
        self.model_name = model_name
        self.container = PodmanContainer(image_name=image_name)

    async def predict(self, prompt: str, **kwargs) -> str:
        """
        Runs the prompt against the podman container.
        """
        api_key = kwargs.get("api_key")
        env = {}
        if api_key:
            env["GEMINI_API_KEY"] = api_key

        args = ["gemini", prompt]

        response_data = await self.container.send_command(args, env)
        
        stdout = response_data.get("stdout", "")
        stderr = response_data.get("stderr", "")
        returncode = response_data.get("returncode", 0)

        if returncode != 0:
            raise RuntimeError(f"Gemini CLI failed (code {returncode}):\n{stderr}\n{stdout}")
        
        return stdout.strip()

    def _cleanup(self):
        """Cleanup method exposed for testing/manual shutdown."""
        self.container.stop()
