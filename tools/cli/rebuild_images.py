"""
CLI tool to force-rebuild Docker/Podman images for benchmarks.

This script iterates through the defined `IMAGE_DEFINITIONS` for Gemini CLI agents
and triggers a rebuild of the container images. It is useful when the agent's
source code or dependencies have changed.
"""

import asyncio
import os
import sys


from dotenv import load_dotenv


load_dotenv()


from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import (

    GeminiCliPodmanAnswerGenerator,
)
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import (
    IMAGE_DEFINITIONS,
)
from benchmarks.answer_generators.gemini_cli_docker.podman_utils import PodmanContainer

from core.api_key_manager import API_KEY_MANAGER


async def main():
    print("Force rebuilding all images in IMAGE_DEFINITIONS...")

    # Filter targets from args if provided
    target_images = sys.argv[1:]

    # Create a dummy container instance to access build logic
    container = PodmanContainer(
        image_name="dummy",
        image_definitions=IMAGE_DEFINITIONS
    )

    if target_images:
        leaves = target_images
    else:
        all_dependencies = set()
        for defn in IMAGE_DEFINITIONS.values():
            for dep in defn.dependencies:
                all_dependencies.add(dep)
        leaves = [name for name in IMAGE_DEFINITIONS if name not in all_dependencies]

    print(f"Target images: {leaves}")

    for image_name in leaves:
        print(f"\n--- Building chain for {image_name} ---")
        # Accessing private method as this is a maintenance script
        await container._build_image_chain(image_name, force=True)

    print("\nAll builds complete.")


if __name__ == "__main__":
    asyncio.run(main())
