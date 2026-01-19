import yaml
import fcntl
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from google.genai import Client, types
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType
from pydantic import BaseModel, Field

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Analyze the following AI benchmark prompt/instruction.
Extract a single, concise one-liner description of the task (the "question").
Ignore boilerplate instructions like "You are an agent...", "Use the following format...", etc.
Focus on the specific coding or reasoning task.

Examples:
Input: "You are a coding assistant. Write a Python function to calculate fibonacci numbers. Use the following tools..."
One-Liner: Write a Python function to calculate fibonacci numbers.

Input: "Fix the following error in the adk library: ImportError: cannot import name 'Agent'..."
One-Liner: Fix ImportError regarding 'Agent' in the adk library.

Prompt:
{prompt}
"""

class CaseOneLiner(BaseModel):
    one_liner: str = Field(..., description="A concise, single-sentence summary of the benchmark task.")

class CaseDocManager:
    """
    Manages the persistent cache of benchmark case one-liner descriptions.
    Uses a YAML file for storage.
    Thread-safe using file locking.
    """
    def __init__(self, doc_path: str = "benchmarks/case_docs_cache.yaml"):
        """
        Initialize the CaseDocManager.
        
        Args:
            doc_path: Path to the yaml file where case docs are cached.
        """
        self.doc_path = Path(doc_path)
        # Ensure directory exists
        self.doc_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"CaseDocManager initialized at {self.doc_path}")

    async def get_one_liner(self, benchmark_name: str, prompt_text: str, model_name: str) -> str:
        """
        Retrieves one-liner from cache or generates it using an LLM.
        
        Args:
            benchmark_name: The unique name of the benchmark case (used as cache key).
            prompt_text: The full prompt text to summarize.
            model_name: The LLM model to use for generation.
            
        Returns:
            The concise one-liner string.
        """
        if not prompt_text:
            return f"No prompt available for {benchmark_name}"

        cache = self._load_cache()
        
        if benchmark_name in cache:
            # Simple string cache
            return cache[benchmark_name]
        
        logger.info(f"Generating one-liner for case '{benchmark_name}' using {model_name}...")
        try:
            one_liner = await self._generate_summary(prompt_text, model_name)
            # Write back with lock
            self._update_cache(benchmark_name, one_liner)
            return one_liner
        except Exception as e:
            logger.error(f"Failed to generate one-liner for {benchmark_name}: {e}")
            return f"(Summary generation failed for {benchmark_name})"

    def _load_cache(self) -> Dict[str, str]:
        """Parses the YAML file."""
        if not self.doc_path.exists():
            return {}
            
        try:
            with open(self.doc_path, "r") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError:
            logger.error("Case cache file is corrupted. Returning empty dict.")
            return {}
        except Exception as e:
            logger.error(f"Error loading case cache: {e}")
            return {}

    def _update_cache(self, key: str, value: str):
        """Updates the YAML file safely."""
        try:
            # Use a file lock to ensure atomic updates
            with open(self.doc_path, "r+") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    try:
                        f.seek(0)
                        cache = yaml.safe_load(f) or {}
                    except yaml.YAMLError:
                        cache = {}
                    
                    cache[key] = value
                    
                    f.seek(0)
                    f.truncate()
                    yaml.dump(cache, f, sort_keys=False)
                    logger.info(f"Persisted one-liner for {key}")
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except FileNotFoundError:
             # Handle race condition
             with open(self.doc_path, "w") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    yaml.dump({key: value}, f, sort_keys=False)
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Failed to write case cache: {e}")

    async def _generate_summary(self, prompt_text: str, model_name: str) -> str:
        """Uses Gemini to generate the one-liner."""
        
        # Truncate prompt if huge
        if len(prompt_text) > 30000:
            prompt_text = prompt_text[:30000] + "\n...(truncated)"
            
        api_key = await API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API)
        if not api_key:
            raise RuntimeError("No API key available for summary generation")
            
        client = Client(api_key=api_key)
        
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
             
        try:
            res_obj = CaseOneLiner.model_validate_json(response.text)
            return res_obj.one_liner
        except Exception as e:
            logger.error(f"Failed to parse one-liner output: {e}")
            raise e

# Global instance
CASE_DOC_MANAGER = CaseDocManager()
