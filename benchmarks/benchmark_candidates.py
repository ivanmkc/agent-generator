import enum
from pathlib import Path
from benchmarks.utils import permute
from benchmarks.api_key_manager import ApiKeyManager
from benchmarks.answer_generators.adk_agents import create_default_adk_agent
from benchmarks.answer_generators.adk_answer_generator import AdkAnswerGenerator
from benchmarks.answer_generators.gemini_cli_docker import (
    GeminiCliPodmanAnswerGenerator,
)
from benchmarks.answer_generators.ground_truth_answer_generator import GroundTruthAnswerGenerator
from benchmarks.answer_generators.trivial_answer_generator import TrivialAnswerGenerator
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import (
        IMAGE_DEFINITIONS,
    )


# Define model constants as enum
class ModelName(enum.StrEnum):
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_3_0_PRO = "gemini-3.0-pro"

api_key_manager = ApiKeyManager()

# Create pre-configured agent instances for AdkAnswerGenerator
agent_flash = create_default_adk_agent(model_name=ModelName.GEMINI_2_5_FLASH)
agent_pro = create_default_adk_agent(model_name=ModelName.GEMINI_2_5_PRO)

_podman_image_dirs = [
    # Path("benchmarks/answer_generators/gemini_cli_docker/base"),
    # Path("benchmarks/answer_generators/gemini_cli_docker/adk-python"),
    Path("benchmarks/answer_generators/gemini_cli_docker/adk-docs-ext"),
    Path("benchmarks/answer_generators/gemini_cli_docker/mcp_context7"),
    # Path("benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner"),
]

CANDIDATE_GENERATORS = list(permute(
    GeminiCliPodmanAnswerGenerator,
    model_name=[ModelName.GEMINI_2_5_FLASH], #, ModelName.GEMINI_2_5_PRO],
    dockerfile_dir=_podman_image_dirs,
    image_definitions=[IMAGE_DEFINITIONS],
    api_key_manager=[api_key_manager]
))

CANDIDATE_GENERATORS.extend([
    # Control generators
    GroundTruthAnswerGenerator(),
    TrivialAnswerGenerator(),
    AdkAnswerGenerator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager,
        enable_workflow=True,
        name="WorkflowAdk(gemini-2.5-flash)"
    ),
])