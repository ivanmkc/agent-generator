from dataclasses import dataclass, field
from typing import List, Dict

IMAGE_PREFIX = "gemini-cli"


@dataclass(frozen=True)
class ImageDefinition:
    source_dir: str
    dockerfile: str
    description: str = "No description provided."
    dependencies: List[str] = field(default_factory=list)
    build_args: Dict[str, str] = field(default_factory=dict)


# Define known images and their build configurations for local Podman.
# Cloud Build configurations are defined in cloudbuild.yaml
IMAGE_DEFINITIONS: Dict[str, ImageDefinition] = {
    f"{IMAGE_PREFIX}:base": ImageDefinition(
        source_dir="base",
        dockerfile="base/Dockerfile",
        description="Base image with Gemini CLI and basic tools.",
    ),
    f"{IMAGE_PREFIX}:adk-python": ImageDefinition(
        source_dir="adk-python",
        dockerfile="adk-python/Dockerfile",
        description="Environment with Gemini CLI and ADK Python library pre-installed.",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
    f"{IMAGE_PREFIX}:mcp_context7": ImageDefinition(
        source_dir="mcp_context7",
        dockerfile="mcp_context7/Dockerfile",
        description="Gemini CLI configured with Context7 (semantic search) MCP server.",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
    f"{IMAGE_PREFIX}:adk-docs-ext": ImageDefinition(
        source_dir="adk-docs-ext",
        dockerfile="adk-docs-ext/Dockerfile",
        description="ADK Python development environment with documentation tools and extensions.",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
    f"{IMAGE_PREFIX}:mcp_adk_agent_runner_basic": ImageDefinition(
        source_dir="mcp_adk_agent_runner_basic",
        dockerfile="mcp_adk_agent_runner_basic/Dockerfile",
        description="MCP-based runner that dynamically loads and executes ADK agent code, managing the full agent lifecycle and capturing execution logs.",
        dependencies=[f"{IMAGE_PREFIX}:adk-python"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:adk-python"},
    ),
    f"{IMAGE_PREFIX}:mcp_adk_agent_runner_smart_search": ImageDefinition(
        source_dir="mcp_adk_agent_runner_smart_search",
        dockerfile="mcp_adk_agent_runner_smart_search/Dockerfile",
        description="Enhanced ADK runner that includes integrated pydoc discovery tools, allowing the agent to research library documentation before executing code.",
        dependencies=[f"{IMAGE_PREFIX}:adk-python"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:adk-python"},
    ),
    f"{IMAGE_PREFIX}:gemini-cli-mcp-context7": ImageDefinition(
        source_dir="mcp_context7",
        dockerfile="mcp_context7/Dockerfile",
        description="Gemini CLI configured with Context7 MCP server.",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
}
