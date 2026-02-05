from pathlib import Path
from typing import Optional
import os

class AppConfig:
    @property
    def TARGET_REPO_URL(self) -> Optional[str]:
        return os.environ.get("TARGET_REPO_URL")
    
    @property
    def TARGET_VERSION(self) -> str:
        return os.environ.get("TARGET_VERSION", "main")
    
    @property
    def TARGET_INDEX_URL(self) -> Optional[str]:
        return os.environ.get("TARGET_INDEX_URL")
    
    @property
    def EMBEDDINGS_FOLDER_PATH(self) -> Optional[Path]:
        val = os.environ.get("EMBEDDINGS_FOLDER_PATH")
        return Path(val) if val else None
    
    @property
    def GEMINI_API_KEY(self) -> Optional[str]:
        return os.environ.get("GEMINI_API_KEY")
    
    @property
    def ADK_SEARCH_PROVIDER(self) -> str:
        return os.environ.get("ADK_SEARCH_PROVIDER", "bm25")

    @property
    def is_local_dev(self) -> bool:
        return bool(os.environ.get("MCP_LOCAL_DEV"))

# Singleton
config = AppConfig()