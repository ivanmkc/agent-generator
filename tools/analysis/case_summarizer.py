import yaml
import fcntl
import logging
import hashlib
import asyncio
import random
from pathlib import Path
from typing import Dict, Any, Optional
from google.genai import Client, types
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType
from pydantic import BaseModel, Field

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_WAIT = 2


SUMMARY_PROMPT = """Analyze the following AI benchmark prompt/instruction.
Extract a single, concise one-liner description of the ACTUAL task or question being asked.
CRITICAL: Ignore generic boilerplate instructions like "You are an agent...", "Use the following format...", "Explore the ADK...", or "Fix or implement...".
Look for the specific technical question or the specific error/feature being tested.

Examples:
Input: "You are a coding assistant. Write a Python function to calculate fibonacci numbers. Use the following tools..."
One-Liner: Write a Python function to calculate fibonacci numbers.

Input: "Fix the following error in the adk library: ImportError: cannot import name 'Agent'..."
One-Liner: Fix ImportError regarding 'Agent' in the adk library.

Input: "You are an expert... Answer the following multiple choice question: Which class allows defining a tool from an OpenAPI spec? ..."
One-Liner: Which class allows defining a tool from an OpenAPI spec?

Input: "Explore the ADK... Task: Find the correct signature for the 'on_event' callback in BasePlugin."
One-Liner: Find the correct signature for the 'on_event' callback in BasePlugin.

Prompt:
{prompt}
"""

class CaseOneLiner(BaseModel):
    one_liner: str = Field(..., description="A concise, single-sentence summary of the benchmark task.")

class CaseDocEntry(BaseModel):
    one_liner: str
    checksum: str

class CaseDocCache(BaseModel):
    cases: Dict[str, CaseDocEntry] = Field(default_factory=dict)

class CaseDocManager:
    """
    Manages the persistent cache of benchmark case one-liner descriptions.
    Uses a YAML file for storage.
    Thread-safe using file locking and Pydantic models for data.
    """
    def __init__(self, doc_path: str = "ai/reports/case_docs_cache.yaml"):
        """
        Initialize the CaseDocManager.
        
        Args:
            doc_path: Path to the yaml file where case docs are cached.
        """
        self.doc_path = Path(doc_path)
        # Ensure directory exists
        self.doc_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"CaseDocManager initialized at {self.doc_path}")

    def _calculate_checksum(self, text: str) -> str:
        """Calculates MD5 checksum of the text."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    async def get_one_liner(self, benchmark_name: str, prompt_text: str, model_name: str) -> str:
        """
        Retrieves one-liner from cache or generates it using an LLM.
        Checks checksum to ensure the prompt hasn't changed.
        
        Args:
            benchmark_name: The unique name of the benchmark case (used as cache key).
            prompt_text: The full prompt text to summarize.
            model_name: The LLM model to use for generation.
            
        Returns:
            The concise one-liner string.
        """
        if not prompt_text:
            return f"No prompt available for {benchmark_name}"

        current_checksum = self._calculate_checksum(prompt_text)
        cache_data = self._load_cache()
        
        if benchmark_name in cache_data.cases:
            entry = cache_data.cases[benchmark_name]
            if entry.checksum == current_checksum:
                return entry.one_liner
            else:
                logger.info(f"Checksum mismatch for '{benchmark_name}'. Regenerating one-liner.")
        
        logger.info(f"Generating one-liner for case '{benchmark_name}' using {model_name}...")
        try:
            one_liner = await self._generate_summary(prompt_text, model_name)
            # Write back with lock
            self._update_cache(benchmark_name, one_liner, current_checksum)
            return one_liner
        except Exception as e:
            logger.error(f"Failed to generate one-liner for {benchmark_name}: {e}")
            return f"(Summary generation failed for {benchmark_name})"

    def _load_cache(self) -> CaseDocCache:
        """Parses the YAML file into CaseDocCache model."""
        if not self.doc_path.exists():
            return CaseDocCache()
            
        try:
            with open(self.doc_path, "r") as f:
                raw_data = yaml.safe_load(f)
                if not raw_data:
                    return CaseDocCache()
                
                # Handle legacy format where it was just a flat dict of string -> string or string -> dict
                if isinstance(raw_data, dict) and "cases" not in raw_data:
                    # Migration logic
                    migrated_cases = {}
                    for k, v in raw_data.items():
                        if isinstance(v, str):
                            # We don't have a checksum for legacy string entries, 
                            # so they will be regenerated on next use.
                            pass 
                        elif isinstance(v, dict) and "one_liner" in v and "checksum" in v:
                            migrated_cases[k] = CaseDocEntry(**v)
                    return CaseDocCache(cases=migrated_cases)
                
                return CaseDocCache.model_validate(raw_data)
        except Exception as e:
            logger.error(f"Error loading case cache: {e}")
            return CaseDocCache()

    def _update_cache(self, key: str, value: str, checksum: str):
        """Updates the YAML file safely using Pydantic models and file locking."""
        try:
            # Use a file lock to ensure atomic updates
            with open(self.doc_path, "a+") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    f.seek(0)
                    content = f.read()
                    if content:
                        raw_data = yaml.safe_load(content)
                        # Reuse _load_cache like logic but in-place
                        if isinstance(raw_data, dict) and "cases" not in raw_data:
                            migrated_cases = {}
                            for k, v in raw_data.items():
                                if isinstance(v, dict) and "one_liner" in v and "checksum" in v:
                                    migrated_cases[k] = CaseDocEntry(**v)
                            cache = CaseDocCache(cases=migrated_cases)
                        else:
                            cache = CaseDocCache.model_validate(raw_data or {"cases": {}})
                    else:
                        cache = CaseDocCache()
                    
                    # Update or add entry
                    cache.cases[key] = CaseDocEntry(one_liner=value, checksum=checksum)
                    
                    # Write back
                    f.seek(0)
                    f.truncate()
                    yaml.dump(cache.model_dump(), f, sort_keys=False)
                    logger.info(f"Persisted one-liner for {key}")
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Failed to write case cache: {e}")

    async def _generate_summary(self, prompt_text: str, model_name: str) -> str:
        """Uses Gemini to generate the one-liner with retries."""
        
        # Truncate prompt if huge
        if len(prompt_text) > 30000:
            prompt_text = prompt_text[:30000] + "\n...(truncated)"

        last_error = None
        
        for attempt in range(MAX_RETRIES):
            api_key, key_id = await API_KEY_MANAGER.get_next_key_with_id(KeyType.GEMINI_API)
            if not api_key:
                raise RuntimeError("No API key available for summary generation")
                
            client = Client(api_key=api_key)
            
            try:
                response = await client.aio.models.generate_content(
                    model=model_name, 
                    contents=[types.Content(parts=[types.Part(text=SUMMARY_PROMPT.format(prompt=prompt_text))])],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=CaseOneLiner
                    )
                )
                
                if not response or not response.text:
                     raise RuntimeError("LLM returned empty response for summary")
                
                # Report success
                await API_KEY_MANAGER.report_result(KeyType.GEMINI_API, key_id, True)

                try:
                    res_obj = CaseOneLiner.model_validate_json(response.text)
                    return res_obj.one_liner
                except Exception as e:
                    logger.error(f"Failed to parse one-liner output: {e}")
                    # If parsing fails, it's not strictly an API error, but we might want to retry generation
                    # or just fail. Let's count it as a failure for the key (maybe the model is acting up)
                    raise e

            except Exception as e:
                last_error = e
                error_msg = str(e)
                logger.warning(f"Summary generation attempt {attempt+1}/{MAX_RETRIES} failed: {error_msg}")
                
                # Report failure to manager (handles cooldowns)
                await API_KEY_MANAGER.report_result(KeyType.GEMINI_API, key_id, False, error_message=error_msg)
                
                # Exponential backoff
                wait_time = BASE_WAIT * (2 ** attempt) + random.random()
                await asyncio.sleep(wait_time)
        
        raise last_error if last_error else RuntimeError("Summary generation failed after retries")

# Global instance
CASE_DOC_MANAGER = CaseDocManager()