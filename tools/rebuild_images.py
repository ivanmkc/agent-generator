import asyncio
import sys
from pathlib import Path

# Add project root to sys.path to allow imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from benchmarks.answer_generators.gemini_cli_docker.gemini_cli_podman_answer_generator import (
    GeminiCliPodmanAnswerGenerator,
)
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import (
    IMAGE_DEFINITIONS,
)


from benchmarks.api_key_manager import API_KEY_MANAGER

async def main():
    print("Force rebuilding all images in IMAGE_DEFINITIONS...")
    
    # Filter targets from args if provided
    target_images = sys.argv[1:]
    
    generator = await GeminiCliPodmanAnswerGenerator.create(
        model_name="dummy",
        api_key_manager=API_KEY_MANAGER,
        image_definitions=IMAGE_DEFINITIONS,
        image_name="dummy"
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
        await generator._build_image_chain(image_name, force=True)

    print("\nAll builds complete.")


if __name__ == "__main__":
    asyncio.run(main())
