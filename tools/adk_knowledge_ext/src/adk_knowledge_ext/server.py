"""
Codebase Knowledge MCP Server.

This module implements a Model Context Protocol (MCP) server that provides tools for:
- Browsing ranked codebase modules.
- Inspecting symbol specifications (classes, functions).
- Reading implementation source code.
- Semantic searching within the codebase.

It supports multiple knowledge bases (repositories), either bundled directly into the
package (for zero-latency offline use) or configured via environment variables.
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Union, List, Dict, Any
from logging.handlers import RotatingFileHandler
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from .index import get_index
from .reader import SourceReader
from .config import config

class KnowledgeBaseConfig(BaseModel):
    """
    Configuration model for a single Knowledge Base (repository).
    
    Attributes:
        id: Unique identifier for the KB (e.g., 'adk-python-v1.20.0').
        repo_url: The Git URL of the repository.
        version: The version tag or branch name.
        index_url: Optional URL to download the pre-computed knowledge index.
        name: Human-readable name.
        description: Description of the codebase.
        source: Origin of the config ('bundled' or 'env').
    """
    id: str
    repo_url: str
    version: str
    index_url: str | None = None
    name: str
    description: str | None = None
    source: str  # "bundled" or "env"

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
    """
    Retrieves or creates a cached SourceReader for the specified repository and version.
    
    Args:
        repo_url: The Git URL of the repository.
        version: The version/branch to read from.
        
    Returns:
        A configured SourceReader instance.
    """
    key = f"{repo_url}@{version}"
    if key not in _readers:
        _readers[key] = SourceReader(repo_url=repo_url, version=version)
    return _readers[key]


import os

def _get_available_kbs() -> Dict[str, KnowledgeBaseConfig]:
    """
    Returns a mapping of KB ID to metadata.
    KB IDs are derived from the bundled registry and environment config.
    Supports V2 hierarchical registry: owner/repo@version.
    """
    kbs = {}
    
    # 1. Load Bundled Registry (V2)
    registry_path = Path(__file__).parent / "registry.yaml"
    if registry_path.exists():
        import yaml
        try:
            registry = yaml.safe_load(registry_path.read_text())
            repos = registry.get("repositories", {})
            
            # If it's old format (no 'repositories' key), fallback
            if not repos and registry:
                 # Legacy V1 fallback
                 for kb_id, meta in registry.items():
                    repo_url = meta["repo_url"]
                    ver = meta["version"]
                    desc = meta.get("description") or f"Codebase knowledge for {repo_url} at version {ver}"
                    kbs[kb_id] = KnowledgeBaseConfig(
                        id=kb_id, repo_url=repo_url, version=ver,
                        name=f"{repo_url.split('/')[-1].replace('.git', '')} ({ver})",
                        description=desc, source="bundled", index_url=meta.get("index_url")
                    )
            else:
                for repo_id, repo_meta in repos.items():
                    repo_url = repo_meta["repo_url"]
                    desc = repo_meta.get("description")
                    default_ver = repo_meta.get("default_version")
                    
                    for ver, ver_meta in repo_meta.get("versions", {}).items():
                        kb_id = f"{repo_id}@{ver}"
                        kb_config = KnowledgeBaseConfig(
                            id=kb_id,
                            repo_url=repo_url,
                            version=ver,
                            name=f"{repo_id} ({ver})",
                            description=desc,
                            source="bundled",
                            index_url=ver_meta.get("index_url")
                        )
                        kbs[kb_id] = kb_config
                        
                        # Add alias for default version
                        if ver == default_ver:
                            kbs[repo_id] = kb_config

        except Exception as e:
            logger.warning(f"Failed to read bundled registry: {e}")

    # 2. Add Configured KBs from env (JSON) - Legacy Support
    configured_kbs_json = os.environ.get("MCP_KNOWLEDGE_BASES")
    
    if configured_kbs_json:
        try:
            items = json.loads(configured_kbs_json)
            for item in items:
                # Support string-only IDs (from registry)
                if isinstance(item, str):
                    if item in kbs:
                        # Clone and mark as active/env
                        existing = kbs[item]
                        kbs[item] = KnowledgeBaseConfig(
                            id=existing.id,
                            repo_url=existing.repo_url,
                            version=existing.version,
                            index_url=existing.index_url,
                            name=existing.name,
                            description=existing.description,
                            source="env"
                        )
                    else:
                        logger.warning(f"Configured KB ID '{item}' not found in registry and no details provided.")
                    continue

                # Support full dictionary config (legacy/custom)
                if isinstance(item, dict):
                    repo_url = item["repo_url"]
                    version = item["version"]
                    
                    # Use explicit ID if provided, otherwise generate one
                    kb_id = item.get("id")
                    if not kb_id:
                        repo_name = repo_url.split("/")[-1].replace(".git", "")
                        kb_id = f"{repo_name}-{version}" if version != "main" else repo_name
                    
                    # Env config overrides bundled if same ID
                    desc = item.get("description")
                    if not desc:
                        desc = f"Configured repository: {repo_url}"

                    kbs[kb_id] = KnowledgeBaseConfig(
                        id=kb_id,
                        repo_url=repo_url,
                        version=version,
                        index_url=item.get("index_url"),
                        name=item.get("name") or f"{kb_id}",
                        description=desc,
                        source="env"
                    )
        except Exception as e:
            logger.warning(f"Failed to parse MCP_KNOWLEDGE_BASES: {e}")

    return kbs


def _validate_kb(kb_id: str | None) -> KnowledgeBaseConfig:
    """Validates kb_id and returns its metadata. Raises if invalid."""
    kbs = _get_available_kbs()
    
    # Smart Defaulting
    if not kb_id or kb_id in ("default", "adk", "active"):
        # If explicitly requesting default, or omitting it, pick the active/env one first
        # Search for one marked as source='env'
        for k, v in kbs.items():
            if v.source == "env":
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
    resolved_id = kb_meta.id
    repo_url = kb_meta.repo_url
    logger.debug(f"Ensuring index for resolved_id={resolved_id} (requested={kb_id})")
    
    idx = get_index(resolved_id)
    if idx._loaded:
        return resolved_id

    index_url = kb_meta.index_url
    
    # 0. Check for file:// URL (Absolute Local Path)
    if index_url and index_url.startswith("file://"):
        local_path = Path(index_url.replace("file://", ""))
        if local_path.exists():
            logger.info(f"Using local file index for {resolved_id}: {local_path}")
            idx.load(local_path)
            return resolved_id

    # 1. Check if the index_url points to a local bundled file
    if index_url and not index_url.startswith("http"):
        # Assume it's a relative path from the 'data' directory
        bundled_path = _BUNDLED_DATA / index_url
        if bundled_path.exists():
            logger.info(f"Using bundled index for {resolved_id}: {bundled_path}")
            idx.load(bundled_path)
            return resolved_id
        # Also check if it's just a filename in data/
        bundled_path_alt = _BUNDLED_DATA / index_url.split("/")[-1]
        if bundled_path_alt.exists():
            logger.info(f"Using bundled index (alt) for {resolved_id}: {bundled_path_alt}")
            idx.load(bundled_path_alt)
            return resolved_id

    # 2. Manual URL Download
    if index_url and index_url.startswith("http"):
        # ... download logic ...
        cache_dir = Path.home() / ".mcp_cache" / "indices"
        cache_dir.mkdir(parents=True, exist_ok=True)
        import hashlib
        url_hash = hashlib.md5(index_url.encode()).hexdigest()[:8]
        cached_index = cache_dir / f"index_{url_hash}.yaml"
        
        if not cached_index.exists():
            logger.info(f"Downloading index from {index_url}...")
            try:
                cmd = ["curl", "-f", "-L", "-o", str(cached_index)]
                # Add auth token if available
                gh_token = os.environ.get("GITHUB_TOKEN")
                if gh_token:
                    cmd.extend(["-H", f"Authorization: token {gh_token}"])
                cmd.append(index_url)
                
                subprocess.run(cmd, check=True)
            except Exception as e:
                logger.error(f"Failed to download index: {e}")
                cached_index = None

        if cached_index:
            idx.load(cached_index)
            return resolved_id

    # 3. Final Failure
    raise RuntimeError(f"Index for '{resolved_id}' ({repo_url}) not properly set up and no download URL available.")


def _ensure_instructions():
    """
    Ensures that the dynamic instructions file is available.
    Generates a compact, version-aware registry summary.
    """
    kbs = _get_available_kbs()
    
    # Group KBs by repository for compact display
    repos = {}
    for kb_id, config in kbs.items():
        # Canonicalize base ID (strip version suffix if present)
        base_id = kb_id.split("@")[0]
        if base_id not in repos:
            repos[base_id] = {"description": config.description, "versions": set()}
        repos[base_id]["versions"].add(config.version)

    registry_lines = ["**KNOWLEDGE BASE REGISTRY:**", "(Format: `kb_id` | Description | Supported Versions)", ""]
    for repo_id, info in repos.items():
        versions_list = sorted(list(info["versions"]), reverse=True)
        versions_str = ", ".join([f"`{v}`" for v in versions_list])
        registry_lines.append(f"*   `{repo_id}` | {info['description']}")
        registry_lines.append(f"    *   Versions: {versions_str}")
        registry_lines.append(f"    *   *Usage:* `list_modules(kb_id=\"{repo_id}@<version>\", ...)`")

    registry_str = "\n".join(registry_lines)
    
    bundled_instr = _BUNDLED_DATA / "INSTRUCTIONS.md"
    template = Path(__file__).parent.parent.parent / "INSTRUCTIONS.template.md"
    content = ""
    
    if template.exists():
        content = template.read_text()
    elif bundled_instr.exists():
        content = bundled_instr.read_text()
    else:
        return

    content = content.replace("{{KB_REGISTRY}}", registry_str)

    cache_path = Path.home() / ".mcp_cache" / "instructions" / "KNOWLEDGE_MCP_SERVER_INSTRUCTION.md"
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
    _ensure_instructions()
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
    
    reader = _get_reader(kb_meta.repo_url, kb_meta.version)
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
                reader = _get_reader(kb_meta.repo_url, kb_meta.version)
                source_snippet = reader.read_source(rel_path, target_fqn, suffix)
            except Exception as e:
                source_snippet = f"(Could not retrieve source: {e})"

        return f"Note: Symbol '{fqn}' is not explicitly indexed. Showing parent symbol '{target.get('id') or target.get('fqn')}'.\n\n{output}\n\n{source_snippet}"

    return output



def main():
    mcp.run()


if __name__ == "__main__":
    main()
