from dataclasses import dataclass, field
from typing import List, Dict

@dataclass(frozen=True)
class ImageDefinition:
    source_dir: str
    dockerfile: str
    dependencies: List[str] = field(default_factory=list)
    build_args: Dict[str, str] = field(default_factory=dict)

DEFAULT_IMAGE_PREFIX = "adk-gemini-sandbox"

# Define known images and their build configurations
IMAGE_DEFINITIONS: Dict[str, ImageDefinition] = {
    "base": ImageDefinition(
        source_dir="base",
        dockerfile="base/Dockerfile",
    ),
    "adk-python": ImageDefinition(
        source_dir="adk-python",
        dockerfile="adk-python/Dockerfile",
        dependencies=["base"],
        build_args={"BASE_IMAGE": "adk-gemini-sandbox:base"},
    ),
    "mcp-context7": ImageDefinition(
        source_dir="gemini-cli-mcp-context7",
        dockerfile="gemini-cli-mcp-context7/Dockerfile",
        dependencies=["base"],
        build_args={"BASE_IMAGE": "adk-gemini-sandbox:base"},
    ),
    "adk-docs-ext": ImageDefinition(
        source_dir="adk-docs-ext",
        dockerfile="adk-docs-ext/Dockerfile",
        dependencies=["base"],
        build_args={"BASE_IMAGE": "adk-gemini-sandbox:base"},
    ),
}
