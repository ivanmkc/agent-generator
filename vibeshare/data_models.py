from typing import Optional, List, Dict
from pydantic import BaseModel
import re

FRAMEWORKS_TO_DETECT = [
    "langchain",
    "genkit",
    "autogpt",
    "Auto-GPT",
    "langgraph",
    "autogen",
    "crewai",
    "llamaindex",
    "replit",
    "semantic kernel",
    "Devin AI",
    "OpenHands",
    "haystack",
    "phidata",
    "agentkit",
    "swarm",
    "controlflow",
    "pydantic ai",
    "smolagents",
    "adk",
    "agent development kit",
    "vertex ai",
    "openai assistants",
    "generative ai python sdk",
    "google-generativeai",
    "gemini api",
    "spring ai",
    "langchain4j",
    "jason",
    "microsoft copilot studio",
    "dialogflow",
    "voiceflow",
    "manychat",
    "openai sdk",
    "openai api",
    "google cloud vertex ai sdk",
    "google-cloud-aiplatform"
]

class VibeshareResult(BaseModel):
    category: str
    prompt: str
    model_name: str
    response: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return not self.success

    @property
    def was_adk_mentioned(self) -> bool:
        """
        Check if ADK or Agent Development Kit is mentioned as a framework.
        Supports variations like:
        - adk
        - adk-python, adk python
        - adk-js, adk js
        - adk-java, adk java
        - adk-go, adk go
        - agent development kit
        """
        if not self.response:
            return False
        
        # Matches 'adk', 'adk-python', 'adk python', 'adk-js', etc. or 'Agent Development Kit'
        # The pattern is:
        # 1. \b(adk ...): Starts with 'adk' word boundary
        # 2. (?:[- ](?:python|js|java|go))?: Optional non-capturing group for suffix
        #    - [- ]: separator (hyphen or space)
        #    - (?:python|js|java|go): one of the languages
        # OR
        # 3. agent development kit
        
        pattern = r"(?i)\b(adk(?:[- ](?:python|js|java|go))?|agent development kit)\b"
        return bool(re.search(pattern, self.response))

    @property
    def mentioned_frameworks(self) -> List[str]:
        """
        Returns a list of frameworks mentioned in the response.
        Excludes frameworks that were explicitly mentioned in the prompt to avoid bias.
        """
        if not self.response:
            return []
        
        detected = []
        for framework in FRAMEWORKS_TO_DETECT:
            pattern = r"(?i)\b" + re.escape(framework) + r"\b"
            # Only include if in response AND NOT in prompt
            if re.search(pattern, self.response) and not re.search(pattern, self.prompt):
                detected.append(framework)
        return detected
    
    def to_dict(self):
        return {
            "category": self.category,
            "prompt": self.prompt,
            "model_name": self.model_name,
            "response": self.response,
            "success": self.success,
            "error_message": self.error_message,
            "was_adk_mentioned": self.was_adk_mentioned,
            "mentioned_frameworks": self.mentioned_frameworks
        }
