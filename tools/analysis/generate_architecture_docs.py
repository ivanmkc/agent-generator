"""
Generates and manages architectural documentation for Answer Generators.
Prioritizes benchmarks/answer_generators/ARCHITECTURES.md.
"""
import logging
import asyncio
import inspect
import random
import re
import fcntl
from pathlib import Path
from typing import Dict, Any, Optional
from google.genai import Client, types
from core.api_key_manager import API_KEY_MANAGER, KeyType
from tools.analysis.architecture_model import AgentArchitectureDocs, ToolDetail, ComponentDetail

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_WAIT = 2

ARCHITECTURES_MD_PATH = Path("benchmarks/answer_generators/ARCHITECTURES.md")

DOCS_PROMPT = """You are a Lead Software Architect. Analyze the following Python code/object representation of an AI Agent (Answer Generator).

Your Goal: Reverse-engineer the architecture and produce a structured design document.

Code/Context:
{context}

Output a structured JSON object matching the requested schema.
"""

class GeneratorDocManager:
    """
    Manages architecture documentation by reading from ARCHITECTURES.md 
    and falling back to LLM generation if missing.
    Automatically appends new architectures to ARCHITECTURES.md.
    """
    
    def __init__(self, architectures_path: Path = ARCHITECTURES_MD_PATH):
        self.architectures_path = architectures_path

    def _parse_architectures_md(self) -> Dict[str, str]:
        """Parses ARCHITECTURES.md into a map of heading -> content."""
        if not self.architectures_path.exists():
            logger.warning(f"{self.architectures_path} not found.")
            return {}

        content = self.architectures_path.read_text()
        # Split by level 2 headers
        sections = re.split(r'\n##\s+', content)
        
        docs_map = {}
        for section in sections[1:]: # Skip the intro
            lines = section.strip().split('\n')
            if not lines:
                continue
            title = lines[0].strip()
            body = '\n'.join(lines[1:]).strip()
            docs_map[title] = body
            
        return docs_map

    def _append_to_architectures_md(self, key: str, content: str):
        """Appends new architecture documentation to ARCHITECTURES.md safely."""
        try:
            with open(self.architectures_path, "a") as f:
                # Basic file locking for safe concurrent writes
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    f.write(f"\n## {key}\n\n{content}\n")
                    logger.info(f"Appended documentation for {key} to {self.architectures_path}")
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Failed to append to {self.architectures_path}: {e}")

    async def get_description(
        self, 
        key: str, 
        candidate_obj: Any, 
        model_name: str
    ) -> str:
        """
        Retrieves architecture docs from ARCHITECTURES.md or generates them.
        """
        # 1. Check ARCHITECTURES.md
        static_docs = self._parse_architectures_md()
        
        # Clean key for matching (it might be 'GeminiCliPodman: gemini-cli:base')
        lookup_key = key
        if ":" in key:
            lookup_key = key.split(":")[-1].strip()

        if lookup_key in static_docs:
            logger.info(f"Found static documentation for {lookup_key} in ARCHITECTURES.md")
            return f"### Architecture Details (from ARCHITECTURES.md)\n\n{static_docs[lookup_key]}"
        
        # 2. Fallback to Dynamic Generation (Undocumented Agents)
        logger.info(f"Architecture for {lookup_key} not found in ARCHITECTURES.md. Generating...")

        context_str = f"Name: {lookup_key}\n"
        if candidate_obj:
            context_str += f"Type: {type(candidate_obj)}\n"
            try:
                if hasattr(candidate_obj, "__class__"):
                    src = inspect.getsource(candidate_obj.__class__)
                    context_str += f"\nSource Code:\n{src[:20000]}..."
            except Exception:
                if hasattr(candidate_obj, "__dict__"):
                    context_str += f"\nAttributes: {candidate_obj.__dict__}\n"
                else:
                    context_str += f"\nString Repr: {str(candidate_obj)}\n"

        try:
            docs = await self._generate_docs(context_str, model_name)
            md_content = docs.to_markdown()
            
            # 3. Persist for future runs
            self._append_to_architectures_md(lookup_key, md_content)
            
            return f"### Architecture Details (LLM Generated & Saved)\n\n{md_content}"
        except Exception as e:
            logger.error(f"Failed to generate docs for {lookup_key}: {e}")
            return f"(Architecture documentation unavailable: {e})"

    async def _generate_docs(
        self, 
        context: str, 
        model_name: str
    ) -> AgentArchitectureDocs:
        last_error = None

        for attempt in range(MAX_RETRIES):
            api_key, key_id = await API_KEY_MANAGER.get_next_key_with_id(
                KeyType.GEMINI_API
            )
            if not api_key:
                raise RuntimeError("No API key available")

            client = Client(api_key=api_key)

            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Content(
                            parts=[types.Part(text=DOCS_PROMPT.format(context=context))]
                        )
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=AgentArchitectureDocs,
                    ),
                )

                if not response or not response.text:
                    raise RuntimeError("LLM returned empty response")

                await API_KEY_MANAGER.report_result(KeyType.GEMINI_API, key_id, True)
                return AgentArchitectureDocs.model_validate_json(response.text)

            except Exception as e:
                last_error = e
                error_msg = str(e)
                logger.warning(
                    f"Docs generation attempt {attempt+1} failed: {error_msg}"
                )
                await API_KEY_MANAGER.report_result(
                    KeyType.GEMINI_API, key_id, False, error_message=error_msg
                )
                await asyncio.sleep(BASE_WAIT * (2**attempt) + random.random())

        raise last_error if last_error else RuntimeError("Docs generation failed")


# Global instance
DOC_MANAGER = GeneratorDocManager()
