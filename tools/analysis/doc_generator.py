import inspect
import json
import os
import fcntl
import logging
from pathlib import Path
from typing import Dict, Any
from google.genai import Client, types
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DOC_GEN_PROMPT = """You are a Technical Writer documenting a software architecture.

Analyze the following Python source code for an AI Agent Generator.
Describe its architecture, focusing on:
1. **Agent Topology:** Sequential, Loop, Hierarchical?
2. **Specialists:** What specific agents (Planner, Retrieval, etc.) are used?
3. **Tools:** What key tools are enabled?
4. **Flow:** How does data flow between agents?

Keep it concise (under 200 words). Use Markdown.

Code:
{code}
"""

class GeneratorDocManager:
    """
    Manages the persistent cache of generator architectural descriptions.
    Thread-safe using file locking.
    """
    def __init__(self, doc_path: str = "benchmarks/generator_internals.md"):
        """
        Initialize the DocManager.
        
        Args:
            doc_path: Path to the markdown file where docs are cached.
        """
        self.doc_path = Path(doc_path)
        # Ensure directory exists
        self.doc_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"DocManager initialized at {self.doc_path}")

    def get_description(self, key: str, generator_obj: Any, model_name: str) -> str:
        """
        Retrieves description from cache or generates it from source code using an LLM.
        
        Args:
            key: The unique archetype key (e.g., "ADK_HYBRID_V47").
            generator_obj: The actual generator instance (to inspect source code).
            model_name: The LLM model to use for generation (REQUIRED).
            
        Returns:
            The architectural description markdown string or a placeholder if generation fails.
        """
        if not model_name:
             raise ValueError("model_name must be provided to generate documentation.")

        cache = self._load_cache()
        
        if key in cache:
            # Check if cache contains an error message (heuristic)
            if "Error analyzing source code" not in cache[key]:
                logger.debug(f"Cache hit for {key}")
                return cache[key]
            else:
                logger.info(f"Invalid cache entry (error) found for {key}. Regenerating...")
        
        logger.info(f"Generating docs for {key} using {model_name}...")
        try:
            description = self._generate_from_code(generator_obj, model_name)
            # Write back with lock
            self._update_cache(key, description)
            return description
        except Exception as e:
            logger.error(f"Failed to generate documentation for {key}: {e}")
            return f"(No detailed static description found for this generator archetype due to analysis error: {e})"

    def _load_cache(self) -> Dict[str, str]:
        """Parses the markdown file into a dict."""
        if not self.doc_path.exists():
            return {}
            
        with open(self.doc_path, "r") as f:
            content = f.read()
            
        archetypes = {}
        current_key = None
        current_lines = []
        
        for line in content.splitlines():
            if line.startswith("### "):
                if current_key:
                    archetypes[current_key] = "\n".join(current_lines).strip()
                current_key = line.strip().replace("### ", "")
                current_lines = []
            elif current_key:
                current_lines.append(line)
                
        if current_key:
            archetypes[current_key] = "\n".join(current_lines).strip()
            
        return archetypes

    def _update_cache(self, key: str, description: str):
        """Appends the new description to the file safely."""
        entry = f"\n### {key}\n- **Model:** `[Injected at Runtime]`\n\n{description}\n\n---\n"
        
        try:
            with open(self.doc_path, "a") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    if key not in self._load_cache():
                        f.write(entry)
                        logger.info(f"Persisted docs for {key}")
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Failed to write cache: {e}")

    def _generate_from_code(self, obj: Any, model_name: str) -> str:
        """Uses Gemini to generate docs from source code. Raises Exception on failure."""
        # 1. Get Source Code
        # Heuristic: inspect the module where the class is defined
        module = inspect.getmodule(obj)
        if not module:
            raise ValueError(f"Could not find source module for {obj}")
            
        source_code = inspect.getsource(module)
        
        # Truncate to avoid context limit
        if len(source_code) > 30000:
            source_code = source_code[:30000] + "\n...(truncated)"
            
        # 2. Call LLM
        api_key = API_KEY_MANAGER.get_next_key(KeyType.GEMINI_API)
        if not api_key:
            raise RuntimeError("No API key available for doc generation")
            
        client = Client(api_key=api_key)
        logger.info(f"Calling LLM ({model_name}) for documentation...")
        
        response = client.models.generate_content(
            model=model_name, 
            contents=DOC_GEN_PROMPT.format(code=source_code)
        )
        
        if not response or not response.text:
             raise RuntimeError(f"LLM returned empty response for documentation of {obj}")
             
        return response.text

# Global instance
DOC_MANAGER = GeneratorDocManager()