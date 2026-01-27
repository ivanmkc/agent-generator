"""
Automatic generation of architectural documentation for agents.

This module inspects the source code of an agent (or its Docker definition) and uses
an LLM to generate a structured description of its capabilities, tools, and prompts.
These descriptions are cached and used in reports to explain *what* system was tested.
"""

import inspect
import yaml
import os
import fcntl
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from google.genai import Client, types
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType
from tools.analysis.architecture_model import AgentArchitectureDocs

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DOC_GEN_PROMPT = """You are a Technical Writer documenting a software architecture.

Analyze the following Python source code for an AI Agent Generator.
Populate the requested schema with a DETAILED technical breakdown.

Code:
{code}
"""


class GeneratorDocManager:
    """
    Manages the persistent cache of generator architectural descriptions.
    Uses a YAML file for storage and Pydantic for structured generation.
    Thread-safe using file locking.
    """

    def __init__(self, doc_path: str = "ai/reports/generator_docs_cache.yaml"):
        """
        Initialize the DocManager.

        Args:
            doc_path: Path to the yaml file where docs are cached.
        """
        self.doc_path = Path(doc_path)
        # Ensure directory exists
        self.doc_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"DocManager initialized at {self.doc_path}")

    async def get_description(
        self, key: str, generator_obj: Any, model_name: str
    ) -> str:
        """
        Retrieves description from cache or generates it from source code using an LLM.

        Args:
            key: The unique archetype key (e.g., "ADK_HYBRID_V47").
            generator_obj: The actual generator instance (to inspect source code). Can be None.
            model_name: The LLM model to use for generation (REQUIRED).

        Returns:
            The architectural description markdown string or a placeholder if generation fails.
        """
        if not model_name:
            raise ValueError("model_name must be provided to generate documentation.")

        cache = self._load_cache()

        if key in cache:
            try:
                # Load from cache dict into Pydantic model
                docs = AgentArchitectureDocs(**cache[key])
                logger.debug(f"Cache hit for {key}")
                return docs.to_markdown()
            except Exception as e:
                logger.warning(
                    f"Failed to parse cached entry for {key}: {e}. Regenerating..."
                )

        if generator_obj is None:
            logger.warning(
                f"No generator object provided for {key}, and no valid cache found."
            )
            return f"(No detailed static description found for this generator archetype. Key: `{key}`)"

        logger.info(f"Generating docs for {key} using {model_name}...")
        try:
            docs_obj = await self._generate_from_code(generator_obj, model_name)
            # Write back with lock
            self._update_cache(key, docs_obj.model_dump())
            return docs_obj.to_markdown()
        except Exception as e:
            logger.error(f"Failed to generate documentation for {key}: {e}")
            return f"(No detailed static description found for this generator archetype due to analysis error: {e})"

    def _load_cache(self) -> Dict[str, Any]:
        """Parses the YAML file."""
        if not self.doc_path.exists():
            return {}

        try:
            with open(self.doc_path, "r") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError:
            logger.error("Cache file is corrupted. Returning empty dict.")
            return {}
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return {}

    def _update_cache(self, key: str, data: Dict[str, Any]):
        """Updates the YAML file safely."""
        try:
            # Use a file lock to ensure atomic updates in concurrent environments
            with open(self.doc_path, "r+") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    try:
                        f.seek(0)
                        cache = yaml.safe_load(f) or {}
                    except yaml.YAMLError:
                        cache = {}

                    cache[key] = data

                    f.seek(0)
                    f.truncate()
                    yaml.dump(cache, f, sort_keys=False)
                    logger.info(f"Persisted docs for {key}")
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except FileNotFoundError:
            # Handle race condition where file created after exists check
            with open(self.doc_path, "w") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    yaml.dump({key: data}, f, sort_keys=False)
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Failed to write cache: {e}")

    async def _generate_from_code(
        self, obj: Any, model_name: str
    ) -> AgentArchitectureDocs:
        """Uses Gemini to generate docs from source code. Raises Exception on failure."""

        source_code = ""

        # 0. Handle Docker/Podman objects specially
        if hasattr(obj, "image_name") and "gemini-cli" in getattr(
            obj, "image_name", ""
        ):
            try:
                from benchmarks.answer_generators.gemini_cli_docker.image_definitions import IMAGE_DEFINITIONS

                image_name = obj.image_name
                if image_name in IMAGE_DEFINITIONS:
                    defn = IMAGE_DEFINITIONS[image_name]
                    base_path = Path("benchmarks/answer_generators/gemini_cli_docker")
                    src_path = base_path / defn.source_dir

                    if src_path.exists():
                        logger.info(
                            f"Reading source files from {src_path} for analysis..."
                        )
                        files_to_read = sorted(
                            list(src_path.glob("*.py"))
                            + list(src_path.glob("INSTRUCTIONS*.md"))
                        )

                        source_parts = [
                            f"--- Docker Image: {image_name} ---",
                            f"Description: {defn.description}",
                        ]

                        for f in files_to_read:
                            if "test_" in f.name or "__pycache__" in str(f):
                                continue
                            try:
                                with open(f, "r", encoding="utf-8") as rf:
                                    source_parts.append(f"\n--- File: {f.name} ---\n")
                                    source_parts.append(rf.read())
                            except Exception as e:
                                logger.warning(f"Failed to read {f}: {e}")

                        source_code = "\n".join(source_parts)
                    else:
                        logger.warning(f"Source dir {src_path} not found.")
                        source_code = (
                            f"Source code not found. Description: {defn.description}"
                        )
            except ImportError:
                logger.warning("Could not import IMAGE_DEFINITIONS.")

        # 1. Fallback / Standard Python Object Analysis
        if not source_code:
            module = inspect.getmodule(obj)
            if not module:
                try:
                    source_code = inspect.getsource(obj.__class__)
                except Exception:
                    raise ValueError(f"Could not find source code for {obj}")
            else:
                source_code = inspect.getsource(module)

        if len(source_code) > 60000:
            source_code = source_code[:60000] + "\n...(truncated)"

        # 2. Call LLM
        api_key = await API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API)
        if not api_key:
            raise RuntimeError("No API key available for doc generation")

        client = Client(api_key=api_key)
        logger.info(f"Calling LLM ({model_name}) for documentation...")

        response = await client.aio.models.generate_content(
            model=model_name,
            contents=[
                types.Content(
                    parts=[types.Part(text=DOC_GEN_PROMPT.format(code=source_code))]
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AgentArchitectureDocs,
            ),
        )

        if not response or not response.text:
            raise RuntimeError(
                f"LLM returned empty response for documentation of {obj}"
            )

        try:
            return AgentArchitectureDocs.model_validate_json(response.text)
        except Exception as e:
            logger.error(f"Failed to parse structured output: {e}")
            raise e


# Global instance
DOC_MANAGER = GeneratorDocManager()
