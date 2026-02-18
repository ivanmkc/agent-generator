"""Image Definitions module."""

from dataclasses import dataclass, field
from typing import List, Dict

IMAGE_PREFIX = "claude-code"


@dataclass(frozen=True)
class ImageDefinition:
    source_dir: str
    dockerfile: str
    description: str = "No description provided."
    dependencies: List[str] = field(default_factory=list)
    build_args: Dict[str, str] = field(default_factory=dict)

IMAGE_DEFINITIONS: Dict[str, ImageDefinition] = {
    f"{IMAGE_PREFIX}:claude-base": ImageDefinition(
        source_dir="claude_cli_docker",
        dockerfile="claude_cli_docker/Dockerfile",
        description="Base image with FastAPI and LiteLLM to serve Claude models.",
        dependencies=[],
    ),
}