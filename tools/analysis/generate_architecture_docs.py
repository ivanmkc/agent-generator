"""
LLM-based documentation generator for architecture definitions.

This module manages a persistent cache of architecture descriptions for the generators.
It analyzes the source code (if available) or configuration of a generator and produces
a concise summary of its strategy, tools, and flow.
"""

import yaml
import fcntl
import logging
import hashlib
import asyncio
import inspect
import random
from pathlib import Path
from typing import Dict, Any, Optional
from google.genai import Client, types
from core.api_key_manager import API_KEY_MANAGER, KeyType
from pydantic import BaseModel, Field

# Configure Logging
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_WAIT = 2


ARCH_PROMPT = """Analyze the following Python code (or configuration) which defines an AI Agent architecture.
Summarize the key components, the flow of control, and how it handles context/tools.

Focus on:
1. **Agent Strategy:** (e.g., ReAct, Plan-and-Solve, Sequential Chain, Loop).
2. **Tools:** What tools are available and how are they used?
3. **Memory/State:** How is context managed (Shared history, isolated state, etc.)?
4. **Special Features:** (e.g., Ranked Retrieval, Post-processing, Verification loops).

Keep the summary concise (under 200 words) and technical.

Code/Config:
{code}
"""


class ArchDocEntry(BaseModel):
    description: str
    checksum: str


class ArchDocCache(BaseModel):
    generators: Dict[str, ArchDocEntry] = Field(default_factory=dict)


class DocManager:
    """
    Manages the persistent cache of generator architecture descriptions.
    """

    def __init__(self, doc_path: str = "ai/reports/generator_docs_cache.yaml"):
        self.doc_path = Path(doc_path)
        self.doc_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"DocManager initialized at {self.doc_path}")

    def _calculate_checksum(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _extract_code(self, candidate_obj: Any) -> str:
        """Attempts to extract source code or relevant config from the candidate."""
        try:
            # 1. If it's a function or class
            if inspect.isfunction(candidate_obj) or inspect.isclass(candidate_obj):
                return inspect.getsource(candidate_obj)
            
            # 2. If it's an instance, try to get the class source
            if hasattr(candidate_obj, "__class__"):
                # specific check for GeminiCliPodmanAnswerGenerator
                if candidate_obj.__class__.__name__ == "GeminiCliPodmanAnswerGenerator":
                    return f"GeminiCliPodmanAnswerGenerator(image_name='{candidate_obj.image_name}', extra_env={getattr(candidate_obj, 'extra_env', {})})"
                
                try:
                    return inspect.getsource(candidate_obj.__class__)
                except Exception:
                    pass

            # 3. Fallback to string representation
            return str(candidate_obj)
        except Exception as e:
            return f"Error extracting code: {e}"

    async def get_description(
        self,
        key: str,
        candidate_obj: Any,
        model_name: str
    ) -> str:
        """
        Retrieves description from cache or generates it using an LLM.
        """
        code_text = self._extract_code(candidate_obj)
        current_checksum = self._calculate_checksum(code_text)
        
        cache_data = self._load_cache()

        if key in cache_data.generators:
            entry = cache_data.generators[key]
            if entry.checksum == current_checksum:
                return entry.description
            else:
                logger.info(f"Checksum mismatch for '{key}'. Regenerating docs.")

        logger.info(f"Generating docs for '{key}' using {model_name}...")
        try:
            desc = await self._generate_summary(code_text, model_name)
            self._update_cache(key, desc, current_checksum)
            return desc
        except Exception as e:
            logger.error(f"Failed to generate docs for {key}: {e}")
            return "(Documentation generation failed)"

    def _load_cache(self) -> ArchDocCache:
        if not self.doc_path.exists():
            return ArchDocCache()
        try:
            with open(self.doc_path, "r") as f:
                raw_data = yaml.safe_load(f)
                if not raw_data:
                    return ArchDocCache()
                return ArchDocCache.model_validate(raw_data)
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return ArchDocCache()

    def _update_cache(self, key: str, value: str, checksum: str):
        try:
            with open(self.doc_path, "a+") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    f.seek(0)
                    content = f.read()
                    if content:
                        raw_data = yaml.safe_load(content)
                        cache = ArchDocCache.model_validate(raw_data or {})
                    else:
                        cache = ArchDocCache()

                    cache.generators[key] = ArchDocEntry(description=value, checksum=checksum)

                    f.seek(0)
                    f.truncate()
                    yaml.dump(cache.model_dump(), f, sort_keys=False)
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Failed to write cache: {e}")

    async def _generate_summary(self, code_text: str, model_name: str) -> str:
        if len(code_text) > 30000:
            code_text = code_text[:30000] + "\n...(truncated)"

        last_error = None
        for attempt in range(MAX_RETRIES):
            api_key, key_id = await API_KEY_MANAGER.get_next_key_with_id(KeyType.GEMINI_API)
            if not api_key:
                raise RuntimeError("No API key available")

            client = Client(api_key=api_key)
            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=[types.Content(parts=[types.Part(text=ARCH_PROMPT.format(code=code_text))])],
                )
                
                if not response or not response.text:
                    raise RuntimeError("Empty response")
                
                await API_KEY_MANAGER.report_result(KeyType.GEMINI_API, key_id, True)
                return response.text
            except Exception as e:
                last_error = e
                await API_KEY_MANAGER.report_result(KeyType.GEMINI_API, key_id, False, error_message=str(e))
                await asyncio.sleep(BASE_WAIT * (2**attempt) + random.random())

        raise last_error if last_error else RuntimeError("Failed after retries")


DOC_MANAGER = DocManager()
