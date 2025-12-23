from benchmarks.utils import permute
from pydantic import BaseModel # Added for _PodmanImageConfigData
from benchmarks.api_key_manager import ApiKeyManager

# Define model constants as enum
class ModelName(StrEnum):
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_3_0_PRO = "gemini-3.0-pro"

api_key_manager = ApiKeyManager()

# Create pre-configured agent instances for AdkAnswerGenerator
agent_flash = create_default_adk_agent(model_name=ModelName.GEMINI_2_5_FLASH)
agent_pro = create_default_adk_agent(model_name=ModelName.GEMINI_2_5_PRO)

# Define a temporary Pydantic model for permute to generate configurations
class _PodmanImageConfigData(BaseModel):
    dockerfile_dir: Path

_podman_image_dirs = [
    Path("benchmarks/answer_generators/gemini_cli_docker/base"),
    Path("benchmarks/answer_generators/gemini_cli_docker/adk-python"),
    Path("benchmarks/answer_generators/gemini_cli_docker/adk-docs-ext"),
    Path("benchmarks/answer_generators/gemini_cli_docker/gemini-cli-mcp-context7"),
    Path("benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner"),
]

# Use permute to generate configurations for each dockerfile_dir
_podman_image_configs = [
    config.model_dump() for config in permute(_PodmanImageConfigData, dockerfile_dir=_podman_image_dirs)
]

CANDIDATE_GENERATORS = [
    GeminiCliPodmanAnswerGenerator(
        model_name=model_name,
        dockerfile_dir=config["dockerfile_dir"],
        image_definitions=IMAGE_DEFINITIONS,
        api_key_manager=api_key_manager,
    )
    for model_name in [ModelName.GEMINI_2_5_FLASH]#, ModelName.GEMINI_2_5_PRO]
    for config in _podman_image_configs
]

CANDIDATE_GENERATORS.extend([
    # Control generators
    GroundTruthAnswerGenerator(),
    TrivialAnswerGenerator(),
])