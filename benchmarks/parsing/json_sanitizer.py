import json
import re
import logging
from typing import Type, Optional, Any
from pydantic import BaseModel
from google.genai import Client, types
from benchmarks.api_key_manager import ApiKeyManager, KeyType

logger = logging.getLogger(__name__)

class JsonSanitizer:
    """
    Sanitizes and extracts structured JSON from potentially unstructured LLM output.
    """
    def __init__(self, api_key_manager: Optional[ApiKeyManager] = None, model_name: str = "gemini-2.0-flash"):
        self.api_key_manager = api_key_manager
        self.model_name = model_name

    def _try_parse(self, text: str, schema: Type[BaseModel]) -> Optional[BaseModel]:
        try:
            return schema.model_validate_json(text)
        except Exception:
            return None

    def _extract_from_code_block(self, text: str) -> Optional[str]:
        """Extracts content from ```json ... ``` blocks."""
        matches = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if matches:
            # Return the last block as it's usually the final answer
            return matches[-1]
        
        # Try generic code block if json specific not found
        matches = re.findall(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if matches:
            return matches[-1]
            
        return None

    async def sanitize(self, text: str, schema: Type[BaseModel], run_id: str) -> BaseModel:
        """
        Attempts to parse text into the given Pydantic schema using a multi-stage fallback strategy.
        
        Raises:
            ValueError: If all extraction methods fail.
        """
        # Stage 1: Direct Parse
        clean_text = text.strip()
        obj = self._try_parse(clean_text, schema)
        if obj:
            return obj

        # Stage 2: Regex Extraction (Code Blocks)
        extracted_text = self._extract_from_code_block(clean_text)
        if extracted_text:
            obj = self._try_parse(extracted_text, schema)
            if obj:
                return obj
        
        # Stage 3: LLM Extraction (The "Smart" Fallback)
        if not self.api_key_manager:
            raise ValueError(f"Failed to parse JSON and no ApiKeyManager provided for LLM fallback. Raw text: {text[:200]}...")

        logger.info(f"JSON Parsing failed. Attempting LLM extraction with {self.model_name}...")
        
        extraction_prompt = (
            f"You are a strict data extraction assistant. \n"
            f"Your task is to extract a valid JSON object matching the following schema from the provided raw text.\n"
            f"Fix any syntax errors (trailing commas, missing quotes) if necessary.\n"
            f"Return ONLY the JSON. No markdown, no conversation.\n\n"
            f"Raw Text:\n{text}\n\n"
            f"Target Schema:\n{schema.model_json_schema()}"
        )

        api_key_id: Optional[str] = None
        client: Optional[Client] = None
        
        try:
            # Use a separate key type or same? Using GEMINI_API for now.
            # We don't want to consume the 'run' quota limit if possible, but we need a key.
            # We'll use get_next_key directly to avoid run-state locking conflicts if any.
            api_key = await self.api_key_manager.get_next_key(KeyType.GEMINI_API)
            if not api_key:
                raise ValueError("No API keys available for sanitizer.")
                
            client = Client(api_key=api_key)
            
            response = await client.aio.models.generate_content(
                model=self.model_name,
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema
                )
            )
            
            if response.text:
                return schema.model_validate_json(response.text)
            else:
                raise ValueError("LLM returned empty response during sanitization.")

        except Exception as e:
            logger.error(f"LLM Sanitization failed: {e}")
            raise ValueError(f"Failed to parse JSON via all methods (Direct, Regex, LLM). Error: {e}") from e
