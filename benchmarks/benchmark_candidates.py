import enum
from pathlib import Path
from benchmarks.utils import permute
from benchmarks.api_key_manager import ApiKeyManager
from benchmarks.answer_generators.adk_agents import (
    create_default_adk_agent, 
    create_workflow_adk_generator, 
    create_structured_workflow_adk_generator,
    create_baseline_workflow_adk_generator
)
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

_selected_images = [
    "gemini-cli:base",
    "gemini-cli:adk-python",
    "gemini-cli:adk-docs-ext",
    "gemini-cli:mcp_context7",
    "gemini-cli:mcp_adk_agent_runner_basic",
    "gemini-cli:mcp_adk_agent_runner_smart_search",
]

CANDIDATE_GENERATORS = []

# Add Gemini CLI Podman-based generators
CANDIDATE_GENERATORS.extend(list(permute(
    GeminiCliPodmanAnswerGenerator,
    model_name=[ModelName.GEMINI_2_5_FLASH], #, ModelName.GEMINI_2_5_PRO],
    image_name=_selected_images,
    image_definitions=[IMAGE_DEFINITIONS],
    api_key_manager=[api_key_manager]
)))

# Add Workflow ADK-based generators
CANDIDATE_GENERATORS.extend([
    create_workflow_adk_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    create_structured_workflow_adk_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Variant with history disabled
    create_structured_workflow_adk_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager,
        use_loop_history=False
    ),
    create_baseline_workflow_adk_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    )
]
)

# Add trivial and ground truth generators
# CANDIDATE_GENERATORS.extend([
#     # Control generators
#     GroundTruthAnswerGenerator(),
#     TrivialAnswerGenerator(),
# ])