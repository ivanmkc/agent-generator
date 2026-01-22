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
from benchmarks.answer_generators.debug_adk_agents import create_react_workflow_adk_generator
from benchmarks.answer_generators.experiment_52 import create_statistical_v32_generator
from benchmarks.answer_generators.experiment_53 import create_statistical_v33_generator
from benchmarks.answer_generators.experiment_54 import create_statistical_v34_generator
from benchmarks.answer_generators.experiment_55 import create_statistical_v35_generator
from benchmarks.answer_generators.experiment_56 import create_statistical_v36_generator
from benchmarks.answer_generators.experiment_57 import create_knowledge_only_v37_generator
from benchmarks.answer_generators.experiment_58 import create_coding_v38_generator
from benchmarks.answer_generators.experiment_62 import create_refined_knowledge_generator_v42
from benchmarks.answer_generators.experiment_64 import create_refined_knowledge_generator_v44
from benchmarks.answer_generators.experiment_65 import create_task_aware_generator_v45
from benchmarks.answer_generators.experiment_66 import create_ranked_index_generator_v46
from benchmarks.answer_generators.experiment_67 import create_hybrid_generator_v47

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
    GEMINI_3_PRO_PREVIEW = "gemini-3-pro-preview"

api_key_manager = ApiKeyManager()

# Define the candidate generators list synchronously.
# This structure is compatible with the current run_benchmarks.py orchestrator
# which expects a list of AnswerGenerator objects and handles async setup() calls explicitly.
CANDIDATE_GENERATORS = [
    GeminiCliPodmanAnswerGenerator(
        image_definitions=IMAGE_DEFINITIONS,
        image_name="gemini-cli:mcp_adk_agent_runner_basic",
        model_name=ModelName.GEMINI_2_5_PRO,
        api_key_manager=api_key_manager
    ),
    GeminiCliPodmanAnswerGenerator(
        image_definitions=IMAGE_DEFINITIONS,
        image_name="gemini-cli:mcp_adk_agent_runner_ranked_knowledge",
        model_name=ModelName.GEMINI_2_5_PRO,
        api_key_manager=api_key_manager,
        extra_env={"ADK_SEARCH_PROVIDER": "bm25"}
    ),
    GeminiCliPodmanAnswerGenerator(
        image_definitions=IMAGE_DEFINITIONS,
        image_name="gemini-cli:mcp_adk_agent_runner_ranked_knowledge",
        model_name=ModelName.GEMINI_2_5_PRO,
        api_key_manager=api_key_manager,
        extra_env={"ADK_SEARCH_PROVIDER": "keyword"}
    ),
]
