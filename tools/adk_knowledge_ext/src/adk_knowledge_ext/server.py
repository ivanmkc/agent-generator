"""Server module."""

import logging
import subprocess
import json
from pathlib import Path
from typing import Union, List
from logging.handlers import RotatingFileHandler
from mcp.server.fastmcp import FastMCP
from .index import get_index
from .reader import SourceReader
from .config import config

# --- Configuration ---

_BUNDLED_DATA = Path(__file__).parent / "data"

# --- Setup ---

# Ensure log directory exists
log_dir = Path.home() / ".mcp_cache" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "codebase-knowledge.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("codebase-knowledge-mcp")
logger.info("Server starting up...")

# Validation
if not config.TARGET_REPO_URL:
    logger.error("TARGET_REPO_URL environment variable is not set. Cloning will be unavailable.")

# Initialize Server
mcp = FastMCP("codebase-knowledge")

# Global reader instance
reader = SourceReader(
    repo_url=config.TARGET_REPO_URL or "",
    version=config.TARGET_VERSION
)


def _ensure_index():
    logger.debug(f"Ensuring index for repo={config.TARGET_REPO_URL}, version={config.TARGET_VERSION}")
    
    # 0. Check for explicit local override via env var (highest priority)
    if config.TARGET_INDEX_PATH and config.TARGET_INDEX_PATH.exists():
        logger.debug(f"Found explicit index at {config.TARGET_INDEX_PATH}")
        get_index().load(config.TARGET_INDEX_PATH)
        return

    # 1. Check Bundled Manifest (Source of Truth)
    manifest_path = _BUNDLED_DATA / "manifest.json"
    if manifest_path.exists() and config.TARGET_REPO_URL:
        try:
            manifest = json.loads(manifest_path.read_text())
            bundled_file = manifest.get(config.TARGET_REPO_URL, {}).get(config.TARGET_VERSION)
            if bundled_file:
                bundled_path = _BUNDLED_DATA / bundled_file
                if bundled_path.exists():
                    logger.info(f"Using bundled index: {bundled_path}")
                    get_index().load(bundled_path)
                    return
        except Exception as e:
            logger.warning(f"Failed to read bundled manifest: {e}")

    # 2. Fallback: Manual URL Download (For custom/new repos)
    # We NO LONGER check registry.yaml at runtime.
    index_url = config.TARGET_INDEX_URL
    if index_url:
        # Save to a user-writable cache
        cache_dir = Path.home() / ".mcp_cache" / "indices"
        cache_dir.mkdir(parents=True, exist_ok=True)
        # Use a hash to prevent filename collisions
        import hashlib
        url_hash = hashlib.md5(index_url.encode()).hexdigest()[:8]
        cached_index = cache_dir / f"index_{url_hash}.yaml"
        
        if cached_index.exists():
            logger.debug(f"Found cached index download at {cached_index}")
            get_index().load(cached_index)
            return
            
        logger.info(f"Downloading index from {index_url}...")
        try:
            subprocess.run(["curl", "-f", "-L", "-o", str(cached_index), index_url], check=True)
            logger.info("Download successful.")
            get_index().load(cached_index)
            return
        except Exception as e:
            logger.error(f"Failed to download index from {index_url}: {e}")

    # 3. Final Failure
    msg = (
        f"This repository ('{config.TARGET_REPO_URL}') is not supported by the Codebase Knowledge MCP server "
        "because its knowledge index is not properly set up.\n\n"
        "TO FIX THIS:\n"
        "1. Run 'codebase-knowledge-mcp-manage setup' for this repository.\n"
        "2. If you are in a restricted environment, use the --knowledge-index-url flag pointing to a local YAML file."
    )
    raise RuntimeError(msg)


def _ensure_instructions():
    """
    Ensures that the dynamic instructions file is available in a user-accessible 
    cache directory.
    """
    bundled_instr = _BUNDLED_DATA / "INSTRUCTIONS.md"
    
    # We always regenerate user-facing instructions to ensure correct metadata
    # regardless of what was bundled.
    template = Path(__file__).parent.parent.parent / "INSTRUCTIONS.template.md"
    content = ""
    
    if template.exists():
        content = template.read_text()
    elif bundled_instr.exists():
        content = bundled_instr.read_text()
    else:
        return

    content = content.replace("{{TARGET_REPO_URL}}", config.TARGET_REPO_URL or "Unknown")
    content = content.replace("{{TARGET_VERSION}}", config.TARGET_VERSION)

    # Copy to a predictable user-writable path
    repo_name = (config.TARGET_REPO_URL or "unknown").split("/")[-1].replace(".git", "")
    cache_path = Path.home() / ".mcp_cache" / "instructions" / f"{repo_name}.md"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    cache_path.write_text(content)
    logger.info(f"System instructions available at: {cache_path}")


@mcp.tool()
def list_modules(page: int = 1, page_size: int = 20) -> str:
    """
    Lists ranked modules and classes in the codebase.

    Args:
        page: Page number (1-based).
        page_size: Number of items per page.
    """
    _ensure_index()
    _ensure_instructions()
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