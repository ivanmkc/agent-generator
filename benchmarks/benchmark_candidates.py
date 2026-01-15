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

# Instantiate candidates
CANDIDATE_GENERATORS = [
    # # Historical baselines can be added here if needed
    
    # # Recent Experiments
    # create_statistical_v32_generator(model_name=ModelName.GEMINI_2_5_FLASH, api_key_manager=api_key_manager),
    # create_statistical_v33_generator(model_name=ModelName.GEMINI_2_5_FLASH, api_key_manager=api_key_manager),
    # create_statistical_v34_generator(model_name=ModelName.GEMINI_2_5_FLASH, api_key_manager=api_key_manager),
    # create_statistical_v35_generator(model_name=ModelName.GEMINI_2_5_FLASH, api_key_manager=api_key_manager),
    # create_statistical_v36_generator(model_name=ModelName.GEMINI_2_5_FLASH, api_key_manager=api_key_manager),
    create_statistical_v35_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        formatter_model=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager,
    ),
    
    # # Decoupled Specialists
    # create_knowledge_only_v37_generator(model_name=ModelName.GEMINI_2_5_PRO, api_key_manager=api_key_manager),
    # # create_coding_v38_generator(model_name=ModelName.GEMINI_2_5_PRO, api_key_manager=api_key_manager), # Disabled (Dummy)
    # create_refined_knowledge_generator_v42(model_name=ModelName.GEMINI_2_5_FLASH, api_key_manager=api_key_manager),
    # create_refined_knowledge_generator_v44(model_name=ModelName.GEMINI_2_5_FLASH, api_key_manager=api_key_manager),
    # create_task_aware_generator_v45(model_name=ModelName.GEMINI_2_5_FLASH, api_key_manager=api_key_manager),
    
    # # Baseline: Gemini CLI with ADK Docs Extension
    # # GeminiCliPodmanAnswerGenerator( ... ) # Disabled due to Podman instability
]
