"""Image Definitions module."""

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
    f"{IMAGE_PREFIX}:adk-docs-ext-starter": ImageDefinition(
        source_dir="adk-docs-ext",
        dockerfile="adk-docs-ext/Dockerfile",
        description="ADK Docs Ext (agent-starter-pack branch)",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={
            "BASE_IMAGE": f"{IMAGE_PREFIX}:base",
            "EXTENSION_REPO": "https://github.com/pierpaolo28/adk-docs-ext",
            "EXTENSION_REF": "agent-starter-pack",
        },
    ),
    f"{IMAGE_PREFIX}:adk-docs-ext-llms": ImageDefinition(
        source_dir="adk-docs-ext",
        dockerfile="adk-docs-ext/Dockerfile",
        description="ADK Docs Ext (llms.txt branch)",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={
            "BASE_IMAGE": f"{IMAGE_PREFIX}:base",
            "EXTENSION_REPO": "https://github.com/pierpaolo28/adk-docs-ext",
            "EXTENSION_REF": "llms.txt",
        },
    ),
    f"{IMAGE_PREFIX}:adk-docs-ext-llms-full": ImageDefinition(
        source_dir="adk-docs-ext",
        dockerfile="adk-docs-ext/Dockerfile",
        description="ADK Docs Ext (llms-full.txt branch)",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={
            "BASE_IMAGE": f"{IMAGE_PREFIX}:base",
            "EXTENSION_REPO": "https://github.com/pierpaolo28/adk-docs-ext",
            "EXTENSION_REF": "llms-full.txt",
        },
    ),
    f"{IMAGE_PREFIX}:mcp_adk_agent_runner_basic": ImageDefinition(
        source_dir="mcp_adk_agent_runner_basic",
        dockerfile="mcp_adk_agent_runner_basic/Dockerfile",
        description="**Baseline Runner:** A minimal execution environment for ADK agents. It can load and run provided agent code but lacks intrinsic tools for code exploration or documentation lookup. It relies entirely on the model's pre-trained knowledge for API usage.",
        dependencies=[f"{IMAGE_PREFIX}:adk-python"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:adk-python"},
    ),
    f"{IMAGE_PREFIX}:mcp_adk_agent_runner_smart_search": ImageDefinition(
        source_dir="mcp_adk_agent_runner_smart_search",
        dockerfile="mcp_adk_agent_runner_smart_search/Dockerfile",
        description="**Smart Discovery Runner:** An enhanced environment equipped with active research tools (`pydoc_search`, `source_browser`). It enables the agent to dynamically look up library documentation and inspect source code *during* the generation loop, allowing it to correct hallucinations and find the right imports.",
        dependencies=[f"{IMAGE_PREFIX}:adk-python"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:adk-python"},
    ),
    f"{IMAGE_PREFIX}:mcp_adk_agent_runner_ranked_knowledge": ImageDefinition(
        source_dir="../../../",
        dockerfile="mcp_adk_agent_runner_ranked_knowledge/Dockerfile",
        description="**Ranked Knowledge Runner (V47 Port):** This runner incorporates the high-fidelity 'Ranked Knowledge Index' from Experiment 67 (V47) directly into the Gemini CLI environment via a custom MCP server. It exposes `search_adk_knowledge` and `inspect_adk_symbol` tools, allowing the CLI agent to perform the same grounded retrieval as the Python-based sequential agent.",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
    f"{IMAGE_PREFIX}:mcp_adk_agent_runner_remote_main": ImageDefinition(
        source_dir="../../../",
        dockerfile="mcp_adk_agent_runner_remote_main/Dockerfile",
        description="**Remote Main Runner:** Tests the production flow where the MCP server is installed directly from the GitHub main branch using uvx.",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
    f"{IMAGE_PREFIX}:gemini-cli-mcp-context7": ImageDefinition(
        source_dir="mcp_context7",
        dockerfile="mcp_context7/Dockerfile",
        description="Gemini CLI configured with Context7 MCP server.",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
    f"{IMAGE_PREFIX}:adk_skill": ImageDefinition(
        source_dir="adk_skill",
        dockerfile="adk_skill/Dockerfile",
        description="Environment with Gemini CLI and the ADK Skill pre-loaded.",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
    f"{IMAGE_PREFIX}:mcp_codebase_knowledge_runner": ImageDefinition(
        source_dir="../../../",
        dockerfile="mcp_codebase_knowledge_runner/Dockerfile",
        description="**Generic Codebase Knowledge Runner:** Uses the repository-agnostic 'Codebase Knowledge' MCP server. It clones the target repository at runtime and provides deep inspection tools (`list_modules`, `read_source_code`).",
        dependencies=[f"{IMAGE_PREFIX}:base"],
        build_args={"BASE_IMAGE": f"{IMAGE_PREFIX}:base"},
    ),
}
