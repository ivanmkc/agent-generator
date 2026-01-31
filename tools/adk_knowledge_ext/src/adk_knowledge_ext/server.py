"""Server module."""

import os
import logging
import subprocess
import json
from pathlib import Path
from typing import Union, List
from mcp.server.fastmcp import FastMCP
from .index import get_index
from .reader import SourceReader

# --- Configuration ---

# Required environment variables
TARGET_REPO_URL = os.environ.get("TARGET_REPO_URL")
TARGET_VERSION = os.environ.get("TARGET_VERSION", "main")
TARGET_INDEX_URL = os.environ.get("TARGET_INDEX_URL")

# Internal paths
_BUNDLED_DATA = Path(__file__).parent / "data" / "indices"
DEFAULT_INDEX_PATH = _BUNDLED_DATA / f"index_{TARGET_VERSION}.yaml"
TARGET_INDEX_PATH = Path(os.environ.get("TARGET_INDEX_PATH", DEFAULT_INDEX_PATH))

# Optional override for local development
env_repo_path = os.environ.get("TARGET_REPO_PATH")
TARGET_REPO_PATH = Path(env_repo_path) if env_repo_path else None

# --- Setup ---

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("codebase-knowledge-mcp")

# Validation
if not TARGET_REPO_URL:
    logger.error("TARGET_REPO_URL environment variable is not set. Cloning will be unavailable.")

# Initialize Server
mcp = FastMCP("codebase-knowledge")

# Global reader instance
reader = SourceReader(
    repo_url=TARGET_REPO_URL or "",
    repo_root=TARGET_REPO_PATH, 
    version=TARGET_VERSION
)


def _ensure_index():
    # 1. If index exists, load it
    if TARGET_INDEX_PATH.exists():
        get_index().load(TARGET_INDEX_PATH)
        return

    # 2. Resolve Index URL (Env > Registry)
    index_url = TARGET_INDEX_URL
    if not index_url and TARGET_REPO_URL:
        registry_path = Path(__file__).parent / "registry.yaml"
        if registry_path.exists():
            import yaml
            try:
                registry = yaml.safe_load(registry_path.read_text())
                repo_map = registry.get(TARGET_REPO_URL, {})
                index_url = repo_map.get(TARGET_VERSION)
                if index_url:
                    logger.info(f"Resolved index URL from registry: {index_url}")
            except Exception as e:
                logger.error(f"Failed to read registry: {e}")

    # 3. If URL is found/provided, try to download
    if index_url:
        # Save to a user-writable cache since bundled dir might be read-only in site-packages
        cache_dir = Path.home() / ".mcp_cache" / "indices"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached_index = cache_dir / f"index_{TARGET_VERSION}.yaml"
        
        if cached_index.exists():
            get_index().load(cached_index)
            return
            
        logger.info(f"Downloading index for {TARGET_VERSION} from {index_url}...")
        try:
            subprocess.run(["curl", "-f", "-o", str(cached_index), index_url], check=True)
            get_index().load(cached_index)
            return
        except Exception as e:
            logger.error(f"Failed to download index: {e}")
            # Fallthrough to error

    raise FileNotFoundError(f"Knowledge index not found at {TARGET_INDEX_PATH} and could not be downloaded (URL missing or failed).")


@mcp.tool()
def list_modules(page: int = 1, page_size: int = 20) -> str:
    """
    Lists ranked modules and classes in the codebase.

    Args:
        page: Page number (1-based).
        page_size: Number of items per page.
    """
    _ensure_index()
    items = get_index().list_items(page, page_size)

    if not items:
        return f"No items found for page {page}."

    lines = [f"--- Ranked Modules (Page {page}) ---"]
    for item in items:
        rank = item.get("rank", "?")
        fqn = item.get("id") or item.get("fqn") or item.get("name") or "unknown"
        type_ = item.get("type", "UNKNOWN")
        lines.append(f"[{rank}] {type_}: {fqn}")

    return "\n".join(lines)


@mcp.tool()
async def search_knowledge(queries: Union[str, List[str]], limit: int = 10) -> str:
    """
    Searches the codebase knowledge base for relevant classes, functions, or concepts.
    Accepts multiple queries to retrieve diverse information in a single call.
    
    Args:
        queries: A single query string or a list of query strings.
        limit: Max total results to return (default: 10).
    """
    _ensure_index()
    
    if isinstance(queries, str):
        queries = [queries]
        
    all_matches_map = {} 
    for query in queries:
        matches = await get_index().search(query, limit)
        for score, item in matches:
            fqn = item.get("id") or item.get("fqn") or item.get("name") or "unknown"
            if fqn not in all_matches_map or score > all_matches_map[fqn][0]:
                all_matches_map[fqn] = (score, item)
    
    if not all_matches_map:
        return f"No matches found."
        
    sorted_matches = sorted(all_matches_map.values(), key=lambda x: x[0], reverse=True)
    final_results = sorted_matches[:limit]
    
    lines = [f"--- Search Results for {len(queries)} queries ---"]
    for score, item in final_results:
        rank = item.get("rank", "?")
        fqn = item.get("id") or item.get("fqn") or item.get("name") or "unknown"
        type_ = item.get("type")
        summary = item.get("docstring", "No summary.")
        summary_short = summary.split("\n")[0][:150]
        lines.append(f"[{rank}] {type_}: {fqn} (Score: {score:.2f})\n    {summary_short}...")

    return "\n".join(lines)


@mcp.tool()
def read_source_code(fqn: str) -> str:
    """
    Reads the implementation source code for a specific symbol from disk.

    Args:
        fqn: The Fully Qualified Name of the symbol.
    """
    _ensure_index()
    target, suffix = get_index().resolve_target(fqn)

    if not target:
        return f"Symbol '{fqn}' not found in index."

    rel_path = target.get("file_path")
    if not rel_path:
        return f"No file path recorded for {fqn}."

    target_fqn = target.get("id") or target.get("fqn") or target.get("name")
    return reader.read_source(rel_path, target_fqn, suffix)


@mcp.tool()
def inspect_symbol(fqn: str) -> str:
    """
    Returns the full structured specification (signatures, docstrings, properties) for a symbol.

    Args:
        fqn: The Fully Qualified Name.
    """
    import yaml
    _ensure_index()
    target, suffix = get_index().resolve_target(fqn)

    if not target:
        return f"Symbol '{fqn}' not found in index."

    output = yaml.safe_dump(target, sort_keys=False)

    if suffix:
        source_snippet = ""
        rel_path = target.get("file_path")
        if rel_path:
            target_fqn = target.get("id") or target.get("fqn") or target.get("name")
            try:
                source_snippet = reader.read_source(rel_path, target_fqn, suffix)
            except Exception as e:
                source_snippet = f"(Could not retrieve source: {e})"

        return f"Note: Symbol '{fqn}' is not explicitly indexed. Showing parent symbol '{target.get('id') or target.get('fqn')}'.\n\n{output}\n\n{source_snippet}"

    return output


def main():
    mcp.run()


if __name__ == "__main__":
    main()
