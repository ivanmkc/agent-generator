import yaml
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
from mcp.server.fastmcp import FastMCP
from adk_agent_tool import run_adk_agent

# Try importing rank_bm25
try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False

# Configuration
RANKED_INDEX_PATH = Path("/app/data/ranked_targets.yaml")
REPO_ROOT = Path("/workdir/repos/adk-python")
SEARCH_PROVIDER_TYPE = os.environ.get("ADK_SEARCH_PROVIDER", "bm25").lower()

# Initialize Server
mcp = FastMCP("adk-knowledge")

# Register Shared Tool
mcp.tool()(run_adk_agent)

# Setup File Logging for Debugging
log_file = Path("/tmp/adk_mcp.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("adk_knowledge_mcp")

# --- Data Loading ---
_INDEX_CACHE: List[Dict[str, Any]] = []
_FQN_MAP: Dict[str, Dict[str, Any]] = {}

# --- Search Provider Interface ---
class SearchProvider(ABC):
    @abstractmethod
    def build_index(self, items: List[Dict[str, Any]]):
        """Builds the search index from the list of items."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int) -> List[Tuple[float, Dict[str, Any]]]:
        """Searches for the query and returns (score, item) tuples."""
        pass

class BM25SearchProvider(SearchProvider):
    def __init__(self):
        self._bm25_index = None
        self._corpus_map = [] # Maps corpus index to _INDEX_CACHE index
        self._items = []

    def build_index(self, items: List[Dict[str, Any]]):
        self._items = items
        if not HAS_BM25:
            logger.warning("rank_bm25 not installed. BM25SearchProvider cannot function.")
            return

        tokenized_corpus = []
        self._corpus_map = []
        
        for i, item in enumerate(items):
            fqn = item.get("id") or item.get("fqn") or item.get("name")
            if fqn:
                # Create a rich text representation for search
                # FQN gets boosted by repetition
                doc_text = f"{fqn} {fqn} {fqn} " + (item.get("docstring") or "")
                tokenized_corpus.append(doc_text.lower().split())
                self._corpus_map.append(i)

        if tokenized_corpus:
            self._bm25_index = BM25Okapi(tokenized_corpus)
            logger.info("BM25 Index built.")

    def search(self, query: str, limit: int) -> List[Tuple[float, Dict[str, Any]]]:
        if not self._bm25_index:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25_index.get_scores(tokenized_query)
        
        # Zip scores with index
        scored_items = []
        for idx, score in enumerate(scores):
            if score > 0:
                scored_items.append((score, idx))
        
        # Sort by score desc
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        matches = []
        top_indices = scored_items[:limit]
        for score, idx in top_indices:
            real_idx = self._corpus_map[idx]
            matches.append((score, self._items[real_idx]))
            
        return matches

class KeywordSearchProvider(SearchProvider):
    def __init__(self):
        self._items = []

    def build_index(self, items: List[Dict[str, Any]]):
        self._items = items
        logger.info("Keyword Search Index ready (no build step needed).")

    def search(self, query: str, limit: int) -> List[Tuple[float, Dict[str, Any]]]:
        matches = []
        keywords = query.lower().split()
        
        for item in self._items:
            fqn_raw = item.get("id") or item.get("fqn") or item.get("name") or ""
            fqn = fqn_raw.lower()
            summary = item.get("docstring", "").lower()
            
            score = 0
            for kw in keywords:
                if kw in fqn:
                    score += 10
                    if fqn.endswith(kw) or fqn.endswith("." + kw):
                        score += 20
                elif kw in summary:
                    score += 5
            
            if score > 0:
                matches.append((score, item))
        
        # Sort by score desc, then by original rank
        matches.sort(key=lambda x: (-x[0], x[1].get("rank", 9999)))
        return matches[:limit]


_SEARCH_PROVIDER: Optional[SearchProvider] = None

def _get_search_provider() -> SearchProvider:
    global _SEARCH_PROVIDER
    if _SEARCH_PROVIDER:
        return _SEARCH_PROVIDER
    
    if SEARCH_PROVIDER_TYPE == "bm25" and HAS_BM25:
        logger.info("Using BM25SearchProvider")
        _SEARCH_PROVIDER = BM25SearchProvider()
    else:
        if SEARCH_PROVIDER_TYPE == "bm25" and not HAS_BM25:
            logger.warning("BM25 requested but not available. Falling back to keyword search.")
        else:
            logger.info(f"Using KeywordSearchProvider (requested: {SEARCH_PROVIDER_TYPE})")
        _SEARCH_PROVIDER = KeywordSearchProvider()
        
    return _SEARCH_PROVIDER


def _load_index():
    global _INDEX_CACHE, _FQN_MAP
    if _INDEX_CACHE:
        return

    if not RANKED_INDEX_PATH.exists():
        logger.error(f"Index not found at {RANKED_INDEX_PATH}")
        return

    try:
        with open(RANKED_INDEX_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            _INDEX_CACHE = data if isinstance(data, list) else []
            
            # Sort by rank (ascending) if not already
            _INDEX_CACHE.sort(key=lambda x: x.get("rank", 9999))
            
            for item in _INDEX_CACHE:
                fqn = item.get("id") or item.get("fqn") or item.get("name")
                if fqn:
                    _FQN_MAP[fqn] = item
            
            # Initialize and build search provider
            provider = _get_search_provider()
            provider.build_index(_INDEX_CACHE)
        
        logger.info(f"Loaded {len(_INDEX_CACHE)} targets from index.")
    except Exception as e:
        logger.error(f"Failed to load index: {e}")

# --- Tools ---

@mcp.tool()
def list_adk_modules(page: int = 1, page_size: int = 20) -> str:
    """
    Lists ranked ADK modules and classes. Use this to explore the API surface. 
    
    Args:
        page: Page number (1-based).
        page_size: Number of items per page.
    """
    _load_index()
    
    start = (page - 1) * page_size
    end = start + page_size
    items = _INDEX_CACHE[start:end]
    
    if not items:
        return f"No items found for page {page}."
        
    lines = [f"--- Ranked Targets (Page {page}) ---"]
    for item in items:
        rank = item.get("rank", "?")
        fqn = item.get("id") or item.get("fqn") or item.get("name") or "unknown"
        type_ = item.get("type", "UNKNOWN")
        lines.append(f"[{rank}] {type_}: {fqn}")
        
    return "\n".join(lines)

@mcp.tool()
def search_adk_knowledge(query: str, limit: int = 10) -> str:
    """
    Searches the ADK knowledge base for relevant classes, functions, or concepts.
    
    Args:
        query: Keywords or natural language query (e.g., 'how to add tools to agent').
        limit: Max results to return.
    """
    _load_index()
    
    provider = _get_search_provider()
    top_matches = provider.search(query, limit)
    
    if not top_matches:
        return f"No matches found for '{query}'."
        
    lines = [f"--- Search Results for '{query}' (Provider: {provider.__class__.__name__}) ---"]
    for score, item in top_matches:
        rank = item.get("rank", "?")
        fqn = item.get("id") or item.get("fqn") or item.get("name") or "unknown"
        type_ = item.get("type")
        summary = item.get("docstring", "No summary.")
        # Truncate summary to first line or 150 chars
        summary_short = summary.split('\n')[0][:150]
        
        lines.append(f"[{rank}] {type_}: {fqn} (Score: {score:.2f})\n    {summary_short}...")
        
    return "\n".join(lines)


@mcp.tool()
def read_adk_source_code(fqn: str) -> str:
    """
    Reads the actual implementation source code for a specific ADK symbol from disk.
    Use this only if the index information (via inspect_adk_symbol) is insufficient.
    
    Args:
        fqn: The Fully Qualified Name (e.g., 'google.adk.agents.llm_agent.LlmAgent').
    """
    _load_index()
    
    target = _FQN_MAP.get(fqn)
    if not target:
        return f"Symbol '{fqn}' not found in index."
        
    rel_path = target.get("file_path")
    if not rel_path:
        return f"No file path recorded for {fqn}."
        
    if rel_path.startswith("env/"):
        full_path = Path("/workdir") / rel_path
    else:
        full_path = REPO_ROOT / rel_path
    
    if not full_path.exists():
        return f"File not found on disk: {full_path}"
        
    try:
        content = full_path.read_text(encoding="utf-8")
        import ast
        tree = ast.parse(content)
        target_name = fqn.split(".")[-1]
        
        extracted_code = None
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == target_name:
                    lines = content.splitlines()
                    start = node.lineno - 1
                    end = node.end_lineno
                    extracted_code = "\n".join(lines[start:end])
                    break
        
        if extracted_code:
            return f"=== Source: {fqn} ===\n\n{extracted_code}"
        else:
            return f"=== File: {rel_path} (Symbol {target_name} not isolated) ===\n\n{content}"

    except Exception as e:
        return f"Error reading file: {e}"

@mcp.tool()
def inspect_adk_symbol(fqn: str) -> str:
    """
    Returns the full structured specification (signatures, docstrings, properties) for a symbol from the ranked index.
    This is the PREFERRED way to understand an API.
    
    Args:
        fqn: The Fully Qualified Name (e.g., 'google.adk.agents.llm_agent.LlmAgent').
    """
    _load_index()
    target = _FQN_MAP.get(fqn)
    if not target:
        return f"Symbol '{fqn}' not found in index."
    
    # Format nicely as YAML/Text
    return yaml.safe_dump(target, sort_keys=False)

if __name__ == "__main__":
    _load_index()
    mcp.run()