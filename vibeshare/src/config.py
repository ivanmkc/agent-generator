"""
Configuration for the VibeShare evaluation suite.

This module defines the models to be evaluated, concurrency limits, and other
global settings for the VibeShare analysis.
"""

from .models.litellm_model import LiteLLMModel
from .models.podman_model import PodmanModel
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import IMAGE_DEFINITIONS

MAX_CONCURRENCY = 4

MODELS = [
    # --- Google Gemini (Updated Jan 2026) ---
    # "gemini-1.5" and "gemini-2.0-pro-exp" are deprecated/retired.
    # Use the stable 2.5 series (January 2025 training data cutoff for above model).
    LiteLLMModel(model_name="gemini/gemini-2.5-flash"),
    LiteLLMModel(model_name="gemini/gemini-2.5-flash-lite"),
    LiteLLMModel(model_name="gemini/gemini-2.5-pro"),
    LiteLLMModel(model_name="gemini/gemini-3-flash-preview"),
    LiteLLMModel(model_name="gemini/gemini-3-pro-preview"),
    # --- Gemini CLI (Podman) ---
    PodmanModel(model_name="gemini-cli-podman/base", image_name="gemini-cli:base", image_definitions=IMAGE_DEFINITIONS),
    PodmanModel(model_name="gemini-cli-podman/adk-python", image_name="gemini-cli:adk-python", image_definitions=IMAGE_DEFINITIONS),
    PodmanModel(model_name="gemini-cli/adk-docs-ext-starter", image_name="gemini-cli:adk-docs-ext-starter", image_definitions=IMAGE_DEFINITIONS),
    PodmanModel(model_name="gemini-cli/adk-docs-ext-llms", image_name="gemini-cli:adk-docs-ext-llms", image_definitions=IMAGE_DEFINITIONS),
    PodmanModel(model_name="gemini-cli/adk-docs-ext-llms-full", image_name="gemini-cli:adk-docs-ext-llms-full", image_definitions=IMAGE_DEFINITIONS),

    # TODO: Add Gemma
    # --- Anthropic Claude (Updated Jan 2026) ---
    # "claude-3-5-sonnet-20241022" was retired in late 2025.
    # The new standard is the 4.5 series.
    LiteLLMModel(model_name="anthropic/claude-sonnet-4-5"),
    LiteLLMModel(model_name="anthropic/claude-opus-4-5"),
    # --- OpenAI (Updated Jan 2026) ---
    LiteLLMModel(model_name="openai/gpt-5.2"),
    LiteLLMModel(model_name="groq/qwen/qwen3-32b"),
    # --- Meta Llama (via Groq) ---
    # Llama 4 is not yet public on Groq. The current SOTA is Llama 3.3.
    LiteLLMModel(model_name="groq/llama-3.3-70b-versatile"),
    # --- xAI Grok ---
    # "grok-2-latest" is an invalid ID. Use the specific model ID.
    LiteLLMModel(model_name="xai/grok-4"),
]