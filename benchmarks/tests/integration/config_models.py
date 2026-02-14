"""
Configuration models for integration tests.

This module defines Pydantic models used to configure generator test cases in `test_config.py`.
It provides type safety and validation for generator settings like Dockerfile paths, image names,
and expected test outcomes.
"""

from typing import List, Literal, Optional, Union
from pathlib import Path
import abc
from pydantic import BaseModel, Field
from benchmarks.data_models import BaseBenchmarkCase
from benchmarks.answer_generators.base import AnswerGenerator
from core.api_key_manager import ApiKeyManager


class GeneratorConfig(BaseModel, abc.ABC):
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
    expected_mcp_servers: List[str] = Field(default_factory=list)
    custom_case: Optional[BaseBenchmarkCase] = None
    expected_tool_uses: List[str] = Field(default_factory=list)
    expected_sub_agent_calls: Optional[List[str]] = Field(default=None)
    strict_order: bool = True

    @abc.abstractmethod
    def create_generator(self, model_name: str, project_id: str) -> AnswerGenerator:
        """
        Factory method to create an AnswerGenerator instance based on this configuration.
        Must be implemented by subclasses.
        """
        pass


class PodmanGeneratorConfig(GeneratorConfig):
    """
    Configuration specific to Podman-based generators.

    Attributes:
        type: Literal "podman".
        dockerfile_dir: Path to the directory containing the Dockerfile.
        image_name: Optional name (tag) of the Docker/Podman image. Derived from dockerfile_dir if omitted.
        service_url: Optional URL if using an existing service (proxy mode).
    """

    type: Literal["podman"] = "podman"
    dockerfile_dir: Path
    image_name: Optional[str] = None
    service_url: Optional[str] = None
    context_instruction: Optional[str] = None
    build_args: Optional[dict[str, str]] = None

    def create_generator(
        self, model_name: str, project_id: str, api_key_manager: ApiKeyManager
    ) -> AnswerGenerator:
        """
        Creates a Podman-based AnswerGenerator instance based on this configuration.
        """
        from benchmarks.answer_generators.gemini_cli_docker import GeminiCliPodmanAnswerGenerator
        from benchmarks.answer_generators.gemini_cli_docker.image_definitions import IMAGE_DEFINITIONS

        image_name = self.image_name
        if not image_name:
            # Logic to find image based on self.dockerfile_dir.name
            source_dir_name = self.dockerfile_dir.name
            for key, defn in IMAGE_DEFINITIONS.items():
                if defn.source_dir == source_dir_name:
                    image_name = key
                    break

        if not image_name:
            # Fallback if still not found, though this likely means a config error
            # But let the generator handle or fail later if we pass None,
            # wait, generator expects valid string.
            # We raise here to be safe.
            raise ValueError(
                f"Could not resolve image name for dockerfile_dir: {self.dockerfile_dir}"
            )

        return GeminiCliPodmanAnswerGenerator(
            model_name=model_name,
            image_name=image_name,
            image_definitions=IMAGE_DEFINITIONS,
            api_key_manager=api_key_manager,
            context_instruction=self.context_instruction,
            build_args=self.build_args,
        )


class WorkflowAdkGeneratorConfig(GeneratorConfig):
    """
    Configuration specific to Workflow ADK-based generators.

    Attributes:
        type: Literal "workflow_adk".
    """

    type: Literal["workflow_adk"] = "workflow_adk"

    def create_generator(
        self, model_name: str, project_id: str, api_key_manager: ApiKeyManager
    ) -> AnswerGenerator:
        """
        Creates a WorkflowAdkAnswerGenerator instance (via factory).
        """
        from benchmarks.answer_generators.adk_agents import create_workflow_adk_generator

        return create_workflow_adk_generator(
            model_name=model_name, api_key_manager=api_key_manager
        )


class StructuredWorkflowAdkGeneratorConfig(GeneratorConfig):
    """
    Configuration specific to Structured Workflow ADK-based generators.

    Attributes:
        type: Literal "structured_workflow_adk".
    """

    type: Literal["structured_workflow_adk"] = "structured_workflow_adk"

    def create_generator(
        self, model_name: str, project_id: str, api_key_manager: ApiKeyManager
    ) -> AnswerGenerator:
        """
        Creates a StructuredWorkflowAdkAnswerGenerator instance (via factory).
        """
        from benchmarks.answer_generators.adk_agents import create_structured_workflow_adk_generator

        return create_structured_workflow_adk_generator(
            model_name=model_name, api_key_manager=api_key_manager
        )


class HybridAdkGeneratorConfig(GeneratorConfig):
    """
    Configuration specific to Hybrid ADK-based generators (V47).

    Attributes:
        type: Literal "hybrid_adk".
    """

    type: Literal["hybrid_adk"] = "hybrid_adk"

    def create_generator(
        self, model_name: str, project_id: str, api_key_manager: ApiKeyManager
    ) -> AnswerGenerator:
        """
        Creates a HybridAdkAnswerGenerator instance (via factory).
        """
        from experiments.experiment_67 import create_hybrid_generator_v47

        return create_hybrid_generator_v47(
            model_name=model_name, api_key_manager=api_key_manager
        )


# Union type for the configuration dictionary values
AnyGeneratorConfig = Union[
    PodmanGeneratorConfig,
    WorkflowAdkGeneratorConfig,
    StructuredWorkflowAdkGeneratorConfig,
    HybridAdkGeneratorConfig,
]
