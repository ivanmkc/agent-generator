"""Server module."""

import logging
import subprocess
import json
from pathlib import Path
from typing import Union, List, Dict, Any
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
# (TARGET_REPO_URL check removed as it is no longer mandatory)

# Initialize Server
mcp = FastMCP("codebase-knowledge")

# Global reader cache
_readers: dict[str, SourceReader] = {}

def _get_reader(repo_url: str, version: str) -> SourceReader:
    key = f"{repo_url}@{version}"
    if key not in _readers:
        _readers[key] = SourceReader(repo_url=repo_url, version=version)
    return _readers[key]


import os

def _get_available_kbs() -> Dict[str, Dict[str, Any]]:
    """
    Returns a mapping of KB ID to metadata.
    KB IDs are derived from the bundled manifest and environment config.
    """
    kbs = {}
    
    # 1. Load Bundled Manifest
    manifest_path = _BUNDLED_DATA / "manifest.yaml"
    if manifest_path.exists():
        import yaml
        try:
            manifest = yaml.safe_load(manifest_path.read_text())
            for repo_url, versions in manifest.items():
                repo_name = repo_url.split("/")[-1].replace(".git", "")
                for ver in versions.keys():
                    kb_id = f"{repo_name}-{ver}" if ver != "main" else repo_name
                    kbs[kb_id] = {
                        "id": kb_id,
                        "repo_url": repo_url,
                        "version": ver,
                        "name": f"{repo_name} ({ver})",
                        "description": f"Codebase knowledge for {repo_url} at version {ver}",
                        "source": "bundled"
                    }
        except Exception as e:
            logger.warning(f"Failed to read bundled manifest for discovery: {e}")

    # 2. Add Configured KBs from env (JSON)
    configured_kbs_json = os.environ.get("MCP_KNOWLEDGE_BASES")
    
    if configured_kbs_json:
        try:
            items = json.loads(configured_kbs_json)
            for item in items:
                repo_url = item["repo_url"]
                version = item["version"]
                repo_name = repo_url.split("/")[-1].replace(".git", "")
                kb_id = f"{repo_name}-{version}" if version != "main" else repo_name
                
                # Env config overrides bundled if same ID
                kbs[kb_id] = {
                    "id": kb_id,
                    "repo_url": repo_url,
                    "version": version,
                    "index_url": item.get("index_url"),
                    "name": f"{repo_name} ({version})",
                    "description": f"Configured repository: {repo_url}",
                    "source": "env"
                }
        except Exception as e:
            logger.warning(f"Failed to parse MCP_KNOWLEDGE_BASES: {e}")

    return kbs


def _validate_kb(kb_id: str | None) -> Dict[str, Any]:
    """Validates kb_id and returns its metadata. Raises if invalid."""
    kbs = _get_available_kbs()
    
    # Smart Defaulting
    if not kb_id or kb_id in ("default", "adk", "active"):
        # If explicitly requesting default, or omitting it, pick the active/env one first
        # Search for one marked as source='env'
        for k, v in kbs.items():
            if v.get("source") == "env":
                logger.debug(f"Resolved kb_id='{kb_id}' to default env KB: '{k}'")
                return v
        
        # Fallback to the first one available
        if kbs:
            first_key = next(iter(kbs))
            logger.debug(f"Resolved kb_id='{kb_id}' to first available KB: '{first_key}'")
            return kbs[first_key]
            
        raise ValueError("No Knowledge Bases loaded. Cannot resolve default kb_id.")

    if kb_id in kbs:
        return kbs[kb_id]
    
    # Helpful rejection
    import difflib
    suggestions = difflib.get_close_matches(kb_id, kbs.keys(), n=3, cutoff=0.5)
    
    msg = f"Knowledge Base '{kb_id}' not found."
    if suggestions:
        msg += f"\n\nDid you mean:\n" + "\n".join([f"- '{s}'" for s in suggestions])
    
    raise ValueError(msg)


def _ensure_index(kb_id: str | None) -> str:
    """Ensures index is loaded and returns the resolved kb_id."""
    kb_meta = _validate_kb(kb_id)
    resolved_id = kb_meta["id"]
    logger.debug(f"Ensuring index for resolved_id={resolved_id} (requested={kb_id})")
    
    repo_url = kb_meta["repo_url"]
    version = kb_meta["version"]
    
    idx = get_index(resolved_id)
    if idx._loaded:
        return resolved_id

    # 1. Check Bundled Manifest
    manifest_path = _BUNDLED_DATA / "manifest.yaml"
    if manifest_path.exists():
        import yaml
        try:
            manifest = yaml.safe_load(manifest_path.read_text())
            bundled_file = manifest.get(repo_url, {}).get(version)
            if bundled_file:
                bundled_path = _BUNDLED_DATA / bundled_file
                if bundled_path.exists():
                    logger.info(f"Using bundled index for {resolved_id}: {bundled_path}")
                    idx.load(bundled_path)
                    return resolved_id
        except Exception as e:
            logger.warning(f"Failed to read bundled manifest: {e}")

    # 2. Manual URL Download (from configured metadata)
    index_url = kb_meta.get("index_url")

    if index_url:
        # ... download logic ...
        cache_dir = Path.home() / ".mcp_cache" / "indices"
        cache_dir.mkdir(parents=True, exist_ok=True)
        import hashlib
        url_hash = hashlib.md5(index_url.encode()).hexdigest()[:8]
        cached_index = cache_dir / f"index_{url_hash}.yaml"
        
        if not cached_index.exists():
            logger.info(f"Downloading index from {index_url}...")
            try:
                subprocess.run(["curl", "-f", "-L", "-o", str(cached_index), index_url], check=True)
            except Exception as e:
                logger.error(f"Failed to download index: {e}")
                cached_index = None

        if cached_index:
            idx.load(cached_index)
            return resolved_id

    # 3. Final Failure
    raise RuntimeError(f"Index for '{resolved_id}' ({repo_url}) not properly set up and no download URL available.")


def _ensure_instructions(kb_id: str | None):
    """
    Ensures that the dynamic instructions file is available.
    """
    kb_meta = _validate_kb(kb_id)
    resolved_id = kb_meta["id"]
    repo_url = kb_meta["repo_url"]
    version = kb_meta["version"]
    
    kbs = _get_available_kbs()
    import yaml
    registry_str = yaml.safe_dump(list(kbs.values()), sort_keys=False)
    
    bundled_instr = _BUNDLED_DATA / "INSTRUCTIONS.md"
    template = Path(__file__).parent.parent.parent / "INSTRUCTIONS.template.md"
    content = ""
    
    if template.exists():
        content = template.read_text()
    elif bundled_instr.exists():
        content = bundled_instr.read_text()
    else:
        return

    content = content.replace("{{TARGET_REPO_URL}}", repo_url)
    content = content.replace("{{TARGET_VERSION}}", version)
    content = content.replace("{{KB_REGISTRY}}", registry_str)
    content = content.replace("{{CURRENT_KB_ID}}", resolved_id)

    repo_name = repo_url.split("/")[-1].replace(".git", "")
    cache_path = Path.home() / ".mcp_cache" / "instructions" / f"{repo_name}.md"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    cache_path.write_text(content)


@mcp.tool()
def list_modules(kb_id: str = None, page: int = 1, page_size: int = 20) -> str:
    """
    Lists ranked modules and classes in the specified codebase.

    Args:
        kb_id: The ID of the knowledge base to query (optional).
        page: Page number (1-based).
        page_size: Number of items per page.
    """
    resolved_id = _ensure_index(kb_id)
    _ensure_instructions(resolved_id)
    items = get_index(resolved_id).list_items(page, page_size)

    if not items:
        return f"No items found for page {page} in '{resolved_id}'."

    lines = [f"--- Ranked Modules in '{resolved_id}' (Page {page}) ---"]
    for item in items:
        rank = item.get("rank", "?")
        fqn = item.get("id") or item.get("fqn") or item.get("name") or "unknown"
        type_ = item.get("type", "UNKNOWN")
        lines.append(f"[{rank}] {type_}: {fqn}")

    return "\n".join(lines)


@mcp.tool()
async def search_knowledge(kb_id: str = None, queries: Union[str, List[str]] = [], limit: int = 10) -> str:
    """
    Searches the specified knowledge base for relevant classes, functions, or concepts.
    
    Args:
        kb_id: The ID of the knowledge base to query (optional).
        queries: A single query string or a list of query strings.
        limit: Max total results to return (default: 10).
    """
    if not queries:
        return "Please provide at least one query string."

    resolved_id = _ensure_index(kb_id)
    
    if isinstance(queries, str):
        queries = [queries]
        
    idx = get_index(resolved_id)
    all_matches_map = {} 
    for query in queries:
        matches = await idx.search(query, limit)
        for score, item in matches:
            fqn = item.get("id") or item.get("fqn") or item.get("name") or "unknown"
            if fqn not in all_matches_map or score > all_matches_map[fqn][0]:
                all_matches_map[fqn] = (score, item)
    
    if not all_matches_map:
        return f"No matches found in '{resolved_id}'."
        
    sorted_matches = sorted(all_matches_map.values(), key=lambda x: x[0], reverse=True)
    final_results = sorted_matches[:limit]
    
    lines = [f"--- Search Results in '{resolved_id}' for {len(queries)} queries ---"]
    for score, item in final_results:
        rank = item.get("rank", "?")
        fqn = item.get("id") or item.get("fqn") or item.get("name") or "unknown"
        type_ = item.get("type")
        summary = item.get("docstring", "No summary.")
        summary_short = summary.split("\n")[0][:150]
        lines.append(f"[{rank}] {type_}: {fqn} (Score: {score:.2f})\n    {summary_short}...")

    return "\n".join(lines)


@mcp.tool()
def read_source_code(kb_id: str = None, fqn: str = "") -> str:
    """
    Reads the implementation source code for a specific symbol from the specified KB.

    Args:
        kb_id: The ID of the knowledge base (optional).
        fqn: The Fully Qualified Name of the symbol.
    """
    if not fqn:
        return "Please provide the Fully Qualified Name (fqn) of the symbol to read."

    resolved_id = _ensure_index(kb_id)
    kb_meta = _validate_kb(resolved_id)
    
    idx = get_index(resolved_id)
    target, suffix = idx.resolve_target(fqn)

    if not target:
        return f"Symbol '{fqn}' not found in index '{resolved_id}'."

    rel_path = target.get("file_path")
    if not rel_path:
        return f"No file path recorded for {fqn} in '{resolved_id}'."

    target_fqn = target.get("id") or target.get("fqn") or target.get("name")
    
    reader = _get_reader(kb_meta["repo_url"], kb_meta["version"])
    return reader.read_source(rel_path, target_fqn, suffix)


@mcp.tool()
def inspect_symbol(kb_id: str = None, fqn: str = "") -> str:
    """
    Returns the full structured specification (signatures, docstrings, properties) for a symbol.

    Args:
        kb_id: The ID of the knowledge base (optional).
        fqn: The Fully Qualified Name.
    """
    if not fqn:
        return "Please provide the Fully Qualified Name (fqn) of the symbol to inspect."

    import yaml
    resolved_id = _ensure_index(kb_id)
    kb_meta = _validate_kb(resolved_id)
    
    idx = get_index(resolved_id)
    target, suffix = idx.resolve_target(fqn)

    if not target:
        return f"Symbol '{fqn}' not found in index '{resolved_id}'."

    output = yaml.safe_dump(target, sort_keys=False)

    if suffix:
        source_snippet = ""
        rel_path = target.get("file_path")
        if rel_path:
            target_fqn = target.get("id") or target.get("fqn") or target.get("name")
            try:
                reader = _get_reader(kb_meta["repo_url"], kb_meta["version"])
                source_snippet = reader.read_source(rel_path, target_fqn, suffix)
            except Exception as e:
                source_snippet = f"(Could not retrieve source: {e})"

        return f"Note: Symbol '{fqn}' is not explicitly indexed. Showing parent symbol '{target.get('id') or target.get('fqn')}'.\n\n{output}\n\n{source_snippet}"

    return output



def main():
    mcp.run()


if __name__ == "__main__":
    main()
