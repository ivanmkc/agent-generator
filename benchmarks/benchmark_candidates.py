"""
Benchmark Candidates Definition.

This module defines the list of candidate answer generators (agents) that will be evaluated
during a benchmark run. It sets up the specific configurations, models, and environment variables
for each candidate. It also defines the ModelName enum for consistent model referencing.
"""

import enum
from pathlib import Path
from core.api_key_manager import ApiKeyManager
from benchmarks.utils import permute
from benchmarks.answer_generators.adk_agents import (
    create_default_adk_agent,
    create_workflow_adk_generator,
    create_structured_workflow_adk_generator,
    create_baseline_workflow_adk_generator,
)
from benchmarks.answer_generators.debug_adk_agents import create_react_workflow_adk_generator
from experiments.experiment_66 import create_ranked_index_generator_v46
from experiments.experiment_67 import create_hybrid_generator_v47
from experiments.experiment_68 import create_mcp_ranked_generator_v68

from benchmarks.answer_generators.gemini_cli_docker import (
    GeminiCliPodmanAnswerGenerator,
)
from benchmarks.answer_generators.ground_truth import GroundTruthAnswerGenerator
from benchmarks.answer_generators.trivial import TrivialAnswerGenerator
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import (
    IMAGE_DEFINITIONS,
)
from core.models import ModelName


api_key_manager = ApiKeyManager()

# Create pre-configured agent instances for AdkAnswerGenerator
agent_flash = create_default_adk_agent(model_name=ModelName.GEMINI_2_5_FLASH)
agent_pro = create_default_adk_agent(model_name=ModelName.GEMINI_2_5_PRO)

_selected_images = [
    "gemini-cli:base",
    "gemini-cli:adk-python",
    "gemini-cli:adk-docs-ext",
    # "gemini-cli:mcp_context7",
    "gemini-cli:adk-docs-ext-starter",
    "gemini-cli:adk-docs-ext-llms",
    "gemini-cli:adk-docs-ext-llms-full",
    # "gemini-cli:mcp_adk_agent_runner_basic",
    # "gemini-cli:mcp_adk_agent_runner_smart_search",
    "gemini-cli:adk_skill",
]

CANDIDATE_GENERATORS = []

# # Add Gemini CLI Podman-based generators
# CANDIDATE_GENERATORS.extend(list(permute(
#     GeminiCliPodmanAnswerGenerator,
#     model_name=[ModelName.GEMINI_2_5_FLASH], #, ModelName.GEMINI_2_5_PRO],
#     image_name=_selected_images,
#     image_definitions=[IMAGE_DEFINITIONS],
#     api_key_manager=[api_key_manager]
# )))

# # Add Workflow ADK-based generators
# CANDIDATE_GENERATORS.extend([
#     create_workflow_adk_generator(
#         model_name=ModelName.GEMINI_2_5_FLASH,
#         api_key_manager=api_key_manager
#     ),
#     create_structured_workflow_adk_generator(
#         model_name=ModelName.GEMINI_2_5_FLASH,
#         api_key_manager=api_key_manager
#     ),
#     # Variant with history disabled
#     create_structured_workflow_adk_generator(
#         model_name=ModelName.GEMINI_2_5_FLASH,
#         api_key_manager=api_key_manager,
#         use_loop_history=False
#     ),
#     create_baseline_workflow_adk_generator(
#         model_name=ModelName.GEMINI_2_5_FLASH,
#         api_key_manager=api_key_manager
#     )
# ])

# Add locally active generator (from HEAD)
CANDIDATE_GENERATORS.append(
    GeminiCliPodmanAnswerGenerator(
        image_definitions=IMAGE_DEFINITIONS,
        image_name="gemini-cli:mcp_adk_agent_runner_ranked_knowledge",
        model_name=ModelName.GEMINI_2_5_FLASH,
        api_key_manager=api_key_manager,
        extra_env={"ADK_SEARCH_PROVIDER": "vector"},
        experiment_id="ranked_knowledge_vector",
    )
)

# # WARNING: This generator relies on the codebase-knowledge MCP server but DOES NOT 
# # provide a pre-computed YAML index. In its current implementation, the MCP tools 
# # (search_knowledge, inspect_symbol, etc.) will FAIL with a RuntimeError.
# CANDIDATE_GENERATORS.append(
#     GeminiCliPodmanAnswerGenerator(
#         image_definitions=IMAGE_DEFINITIONS,
#         image_name="gemini-cli:mcp_codebase_knowledge_runner",
#         model_name=ModelName.GEMINI_2_5_FLASH,
#         api_key_manager=api_key_manager,
#         experiment_id="codebase_knowledge_v1",
#     )
# )


# # Experimental: Python-native port of the MCP Ranked Knowledge agent.
# # Relies on the host's local 'ranked_targets.yaml' file for retrieval.
# CANDIDATE_GENERATORS.append(
#     create_mcp_ranked_generator_v68(
#         model_name=ModelName.GEMINI_2_5_FLASH,
#         api_key_manager=api_key_manager
#     )
# )
