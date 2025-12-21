from dataclasses import dataclass, field
from typing import List, Dict

IMAGE_PREFIX = "gemini-cli"

@dataclass(frozen=True)
class ImageDefinition:
    source_dir: str
    dockerfile: str
    dependencies: List[str] = field(default_factory=list)
    build_args: Dict[str, str] = field(default_factory=dict)

# Define known images and their build configurations for local Podman.
# Cloud Build configurations are defined in cloudbuild.yaml
IMAGE_DEFINITIONS: Dict[str, ImageDefinition] = {
    f"{IMAGE_PREFIX}:base": ImageDefinition(
        source_dir="base",
        dockerfile="base/Dockerfile",
    ),
    f"{IMAGE_PREFIX}:adk-python": ImageDefinition(
        source_dir="adk-python",
        dockerfile="adk-python/Dockerfile",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
    f"{IMAGE_PREFIX}:mcp-context7": ImageDefinition(
        source_dir="gemini-cli-mcp-context7",
        dockerfile="gemini-cli-mcp-context7/Dockerfile",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
    f"{IMAGE_PREFIX}:adk-docs-ext": ImageDefinition(
        source_dir="adk-docs-ext",
        dockerfile="adk-docs-ext/Dockerfile",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
    f"{IMAGE_PREFIX}:mcp-adk-agent-runner": ImageDefinition(
        source_dir="mcp-adk-agent-runner",
        dockerfile="mcp-adk-agent-runner/Dockerfile",
        dependencies=[f"{IMAGE_PREFIX}:adk-python"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:adk-python"},
    ),
}
