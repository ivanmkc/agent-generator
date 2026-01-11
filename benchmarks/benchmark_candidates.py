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
from benchmarks.answer_generators.experiment_22 import create_statistical_v2_generator
from benchmarks.answer_generators.experiment_23 import create_statistical_v3_generator
from benchmarks.answer_generators.experiment_24 import create_statistical_v4_generator
from benchmarks.answer_generators.experiment_25 import create_statistical_v5_generator
from benchmarks.answer_generators.experiment_26 import create_statistical_v6_generator
from benchmarks.answer_generators.experiment_27 import create_statistical_v7_generator
from benchmarks.answer_generators.experiment_29 import create_statistical_v9_generator
from benchmarks.answer_generators.experiment_30 import create_statistical_v10_generator
from benchmarks.answer_generators.experiment_31 import create_statistical_v11_generator
from benchmarks.answer_generators.experiment_32 import create_statistical_v12_generator
from benchmarks.answer_generators.experiment_33 import create_statistical_v13_generator
from benchmarks.answer_generators.experiment_34 import create_statistical_v14_generator
from benchmarks.answer_generators.experiment_35 import create_statistical_v15_generator
from benchmarks.answer_generators.experiment_36 import create_statistical_v16_generator
from benchmarks.answer_generators.experiment_37 import create_statistical_v17_generator
from benchmarks.answer_generators.experiment_38 import create_statistical_v18_generator
from benchmarks.answer_generators.experiment_39 import create_statistical_v19_generator
from benchmarks.answer_generators.experiment_40 import create_statistical_v20_generator
from benchmarks.answer_generators.experiment_41 import create_statistical_v21_generator
from benchmarks.answer_generators.experiment_42 import create_statistical_v22_generator
from benchmarks.answer_generators.experiment_43 import create_statistical_v23_generator
from benchmarks.answer_generators.experiment_44 import create_statistical_v24_generator
from benchmarks.answer_generators.experiment_45 import create_statistical_v25_generator
from benchmarks.answer_generators.experiment_46 import create_statistical_v26_generator
from benchmarks.answer_generators.experiment_47 import create_statistical_v27_generator
from benchmarks.answer_generators.experiment_48 import create_statistical_v28_generator
from benchmarks.answer_generators.experiment_49 import create_statistical_v29_generator
from benchmarks.answer_generators.experiment_50 import create_statistical_v30_generator
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
    ),
    # ReAct Workflow (Statistical - Exp 20)
    create_react_workflow_adk_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V2 (Exp 22 - Guide Check)
    create_statistical_v2_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V3 (Exp 23 - Semantic Mapping)
    create_statistical_v3_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V4 (Exp 24 - Proof of Knowledge)
    create_statistical_v4_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V5 (Exp 25 - Proof + read_file)
    create_statistical_v5_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V6 (Exp 26 - Signature Compliance)
    create_statistical_v6_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V7 (Exp 27 - Pydantic Kwarg Enforcement)
    create_statistical_v7_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V9 (Exp 29 - Deterministic Retrieval)
    create_statistical_v9_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V10 (Exp 30 - Robust Retrieval)
    create_statistical_v10_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V11 (Exp 31 - Schema Guard)
    create_statistical_v11_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V12 (Exp 32 - Context Awareness)
    create_statistical_v12_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V13 (Exp 33 - Smart Retrieval)
    create_statistical_v13_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V14 (Exp 34 - Type Conservatism)
    create_statistical_v14_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V15 (Exp 35 - Class Preference)
    create_statistical_v15_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V16 (Exp 36 - Canonical Import)
    create_statistical_v16_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V17 (Exp 37 - Validation Table)
    create_statistical_v17_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V18 (Exp 38 - Format Fix & Agent Preference)
    create_statistical_v18_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V19 (Exp 39 - Inheritance Inspection)
    create_statistical_v19_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V20 (Exp 40 - Convergence)
    create_statistical_v20_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V21 (Exp 41 - Super Call)
    create_statistical_v21_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V22 (Exp 42 - Input Access)
    create_statistical_v22_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V23 (Exp 43 - Golden Convergence)
    create_statistical_v23_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V24 (Exp 44 - Event Schema Fix)
    create_statistical_v24_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V25 (Exp 45 - Index Retrieval)
    create_statistical_v25_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V26 (Exp 46 - Targeted Index Retrieval)
    create_statistical_v26_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V27 (Exp 47 - BaseAgent Fallback)
    create_statistical_v27_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V28 (Exp 48 - BaseAgent Fallback + Error Loop)
    create_statistical_v28_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V29 (Exp 49 - Association-Aware Retrieval)
    create_statistical_v29_generator(
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager
    ),
    # Statistical V30 (Exp 50 - Task Delegation)
    # create_statistical_v30_generator(
    #     model_name=ModelName.GEMINI_2_5_FLASH,
    #     api_key_manager=api_key_manager
    # )
]
)

# Add trivial and ground truth generators
CANDIDATE_GENERATORS.extend([
    # Control generators
    GroundTruthAnswerGenerator(),
    TrivialAnswerGenerator(),
])