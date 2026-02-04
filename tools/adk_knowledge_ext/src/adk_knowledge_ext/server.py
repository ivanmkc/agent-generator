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

# Log Git Version
try:
    from ._version_git import GIT_SHA
    logger.info(f"Server Build Version (Git SHA): {GIT_SHA}")
except ImportError:
    logger.info("Server Build Version: Unknown (running from source or unbuilt package)")

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
    """
    kbs = {}
    
    # 1. Load Bundled Registry
    registry_path = Path(__file__).parent / "registry.yaml"
    if registry_path.exists():
        import yaml
        try:
            data = yaml.safe_load(registry_path.read_text())
            if "repositories" in data:
                # Hierarchical Format
                for repo_id, meta in data["repositories"].items():
                    repo_url = meta["repo_url"]
                    base_desc = meta.get("description")
                    default_ver = meta.get("default_version")
                    
                    for ver, v_meta in meta.get("versions", {}).items():
                        # Standard ID: owner/repo@version
                        kb_id = f"{repo_id}@{ver}"
                        
                        desc = v_meta.get("description") or base_desc or f"Codebase: {repo_url}"
                        
                        config = KnowledgeBaseConfig(
                            id=kb_id,
                            repo_url=repo_url,
                            version=ver,
                            name=f"{repo_id} ({ver})",
                            description=desc,
                            source="bundled",
                            index_url=v_meta.get("index_url")
                        )
                        kbs[kb_id] = config
                        
                        # Register default alias if matches
                        if ver == default_ver:
                            kbs[repo_id] = config
            else:
                # Legacy Format Fallback
                for kb_id, meta in data.items():
                    kbs[kb_id] = KnowledgeBaseConfig(
                        id=kb_id,
                        repo_url=meta["repo_url"],
                        version=meta["version"],
                        name=f"{meta['repo_url']} ({meta['version']})",
                        description=meta.get("description"),
                        source="bundled",
                        index_url=meta.get("index_url")
                    )
        except Exception as e:
            logger.warning(f"Failed to read bundled registry: {e}")

    # 2. Add Configured KBs from env (JSON)
    configured_kbs_json = os.environ.get("MCP_KNOWLEDGE_BASES")
    
    if configured_kbs_json:
        try:
            items = json.loads(configured_kbs_json)
            for item in items:
                # Expect 'id', 'repo_url', 'version'
                kb_id = item.get("id")
                repo_url = item["repo_url"]
                version = item["version"]
                
                # Fallback ID generation if missing (legacy env var format)
                if not kb_id:
                    repo_name = repo_url.split("/")[-1].replace(".git", "")
                    kb_id = f"{repo_name}-{version}" if version != "main" else repo_name

                kbs[kb_id] = KnowledgeBaseConfig(
                    id=kb_id,
                    repo_url=repo_url,
                    version=version,
                    index_url=item.get("index_url"),
                    name=item.get("name") or f"{kb_id}",
                    description=item.get("description"),
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
    logger.debug(f"Ensuring index for resolved_id={resolved_id} (requested={kb_id})")
    
    repo_url = kb_meta.repo_url
    version = kb_meta.version
    
    idx = get_index(resolved_id)
    if idx._loaded:
        return resolved_id

    # 1. Check Bundled Registry
    registry_path = Path(__file__).parent / "registry.yaml"
    if registry_path.exists():
        import yaml
        try:
            registry = yaml.safe_load(registry_path.read_text())
            # Lookup by ID directly
            if resolved_id in registry:
                meta = registry[resolved_id]
                # If registry points to a local file path as index_url (legacy/bundling support)
                # We check if it's a file in data/
                idx_val = meta.get("index_url")
                if idx_val and not idx_val.startswith("http"):
                     bundled_path = _BUNDLED_DATA / idx_val
                     if bundled_path.exists():
                        logger.info(f"Using bundled index for {resolved_id}: {bundled_path}")
                        idx.load(bundled_path)
                        return resolved_id
        except Exception as e:
            logger.warning(f"Failed to read bundled registry: {e}")

    # 2. Manual URL Download (from configured metadata)
    index_url = kb_meta.index_url

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
    """
    kbs = _get_available_kbs()
    
    # Group by repo_url for compact display
    from collections import defaultdict
    repos = defaultdict(list)
    for kb in kbs.values():
        # Avoid duplicating alias entries
        # If ID == repo_url (e.g. google/adk-python), skip it in listing if we also have the explicit version
        # But wait, we want to list versions.
        # Let's filter out aliases that are just pointers.
        # Heuristic: if ID contains '@', it's a version. If not, it's an alias (unless legacy).
        # Actually, let's just group everything and deduplicate versions.
        repos[kb.repo_url].append(kb)

    registry_lines = []
    for repo_url, configs in repos.items():
        # Deduplicate by version
        unique_versions = {}
        for c in configs:
            unique_versions[c.version] = c
        
        # Pick description from one of them
        first = next(iter(unique_versions.values()))
        repo_id = "Unknown"
        # Try to extract repo id from the ID if it follows convention
        if "@" in first.id:
            repo_id = first.id.split("@")[0]
        else:
            repo_id = repo_url.split("/")[-1].replace(".git", "")

        registry_lines.append(f"*   `{repo_id}` | {first.description or 'No description'}")
        
        for ver, c in unique_versions.items():
            registry_lines.append(f"    *   Version: `{ver}`")
            registry_lines.append(f"    *   *Usage:* `list_modules(kb_id=\"{c.id}\", ...)`")

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
