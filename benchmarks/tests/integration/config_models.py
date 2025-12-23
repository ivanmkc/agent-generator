"""
Configuration models for integration tests.

This module defines Pydantic models used to configure generator test cases in `test_config.py`.
It provides type safety and validation for generator settings like Dockerfile paths, image names,
and expected test outcomes.
"""

from typing import List, Literal, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field
from benchmarks.data_models import BaseBenchmarkCase

class GeneratorConfig(BaseModel):
    """
    Base configuration for any generator used in integration tests.

    Attributes:
        id: Unique identifier for the generator configuration.
        expected_context_files: List of file paths expected to be loaded into the generator's context.
        expected_extensions: List of Gemini CLI extension IDs expected to be discovered.
        expected_mcp_tools: List of MCP tool names expected to be discovered.
        custom_case: Optional specific benchmark case to run instead of the default.
        expected_tool_uses: List of tool names expected to be used during execution.
    """
    id: str
    expected_context_files: List[str] = Field(default_factory=list)
    expected_extensions: List[str] = Field(default_factory=list)
    expected_mcp_tools: List[str] = Field(default_factory=list)
    custom_case: Optional[BaseBenchmarkCase] = None
    expected_tool_uses: List[str] = Field(default_factory=list)

class PodmanGeneratorConfig(GeneratorConfig):
    """
    Configuration specific to Podman-based generators.

    Attributes:
        type: Literal "podman".
        dockerfile_dir: Path to the directory containing the Dockerfile.
        image_name: Name (tag) of the Docker/Podman image.
        service_url: Optional URL if using an existing service (proxy mode).
    """
    type: Literal["podman"] = "podman"
    dockerfile_dir: Path
    image_name: str
    service_url: Optional[str] = None

class CloudRunGeneratorConfig(GeneratorConfig):
    """
    Configuration specific to Cloud Run-based generators.

    Attributes:
        type: Literal "cloud_run".
        dockerfile_dir: Path to the directory containing the Dockerfile.
        service_name: Name of the Cloud Run service.
        region: Google Cloud region (default: us-central1).
        service_url: Optional URL if using an existing service (proxy mode).
    """
    type: Literal["cloud_run"] = "cloud_run"
    dockerfile_dir: Path
    service_name: str
    region: str = "us-central1"
    service_url: Optional[str] = None

# Union type for the configuration dictionary values
AnyGeneratorConfig = Union[PodmanGeneratorConfig, CloudRunGeneratorConfig]
