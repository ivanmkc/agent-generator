from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional
import os

class AppConfig(BaseSettings):
    # Required for cloning/identification
    TARGET_REPO_URL: Optional[str] = None
    TARGET_VERSION: str = "main"
    
    # Optional overrides
    TARGET_INDEX_URL: Optional[str] = None
    TARGET_INDEX_PATH: Optional[Path] = None
    
    # API Keys
    GEMINI_API_KEY: Optional[str] = None
    
    # Feature Flags
    ADK_SEARCH_PROVIDER: str = "bm25"  # bm25, vector, hybrid

    @property
    def is_local_dev(self) -> bool:
        return bool(os.environ.get("MCP_LOCAL_DEV"))

    class Config:
        env_file = ".env"
        extra = "ignore"

# Singleton
config = AppConfig()
