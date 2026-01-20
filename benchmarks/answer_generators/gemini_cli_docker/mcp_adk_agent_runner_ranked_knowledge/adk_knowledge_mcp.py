
import yaml
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from adk_agent_tool import run_adk_agent

# Configuration
RANKED_INDEX_PATH = Path("/app/data/ranked_targets.yaml")
REPO_ROOT = Path("/workdir/repos/adk-python")

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
            
            # Build Map
            for item in _INDEX_CACHE:
                fqn = item.get("id") or item.get("fqn") or item.get("name")
                if fqn:
                    _FQN_MAP[fqn] = item
        
        logger.info(f"Loaded {_INDEX_CACHE} targets from index.")
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
    Supports multiple keywords.
    
    Args:
        query: Keywords to search for, space-separated (e.g., 'agent bigquery tool').
        limit: Max results to return.
    """
    _load_index()
    
    keywords = query.lower().split()
    matches = []
    
    # Simple scoring: FQN match > Summary match
    for item in _INDEX_CACHE:
        fqn_raw = item.get("id") or item.get("fqn") or item.get("name") or ""
        fqn = fqn_raw.lower()
        summary = item.get("docstring", "").lower()
        
        score = 0
        
        for kw in keywords:
            if kw in fqn:
                score += 10
                # Boost exact suffix match (e.g. searching for 'LlmAgent')
                if fqn.endswith(kw) or fqn.endswith("." + kw):
                    score += 20
            elif kw in summary:
                score += 5
            
        if score > 0:
            matches.append((score, item))
            
    # Sort by score desc, then rank asc
    matches.sort(key=lambda x: (-x[0], x[1].get("rank", 9999)))
    
    top_matches = matches[:limit]
    
    if not top_matches:
        return f"No matches found for '{query}'."
        
    lines = [f"--- Search Results for '{query}' ---"]
    for score, item in top_matches:
        rank = item.get("rank", "?")
        fqn = item.get("id") or item.get("fqn") or item.get("name") or "unknown"
        type_ = item.get("type")
        summary = item.get("docstring", "No summary.")[:100]
        lines.append(f"[{rank}] {type_}: {fqn} (Score: {score})\n    {summary}...")
        
    return "\n".join(lines)

@mcp.tool()
def inspect_adk_symbol(fqn: str) -> str:
    """
    Retrieves the source code and documentation for a specific ADK symbol (Class/Function).
    
    Args:
        fqn: The Fully Qualified Name (e.g., 'google.adk.agents.llm_agent.LlmAgent').
    """
    _load_index()
    
    target = _FQN_MAP.get(fqn)
    if not target:
        return f"Symbol '{fqn}' not found in index. Try listing modules first."
        
    # Resolve path
    # Index path example: src/google/adk/agents/base_agent.py
    rel_path = target.get("file_path")
    if not rel_path:
        return f"No file path recorded for {fqn}."
        
    # Container path mapping
    # Local: src/google/...
    # Container: /workdir/repos/adk-python/src/google/...
    
    # Strip leading 'src/' if present relative to repo root
    # ranker output is relative to repo root usually
    
    # Let's assume ranker output is like "src/google/adk/..."
    full_path = REPO_ROOT / rel_path
    
    if not full_path.exists():
        return f"File not found on disk: {full_path}"
        
    try:
        content = full_path.read_text(encoding="utf-8")
        
        # Simple slicing for class/function definition would require AST parsing.
        # For simplicity in this basic MCP, we return the whole file but truncated?
        # Or ideally, we rely on the fact that V47 tools did AST parsing.
        
        # REUSE V47 LOGIC: Since we can't easily port the heavy AST logic into this single script without 
        # copying the whole 'tools' library, we will return the Whole File for now, 
        # but warn about size.
        # Or better: We just read the file. The LLM has a large context window (2.5 Flash).
        
        # Improvement: If it's a class, try to find the class block.
        # Minimal AST parser
        import ast
        tree = ast.parse(content)
        target_name = fqn.split(".")[-1]
        
        extracted_code = None
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == target_name:
                    # Found it!
                    lines = content.splitlines()
                    # ast end_lineno is 1-based
                    start = node.lineno - 1
                    end = node.end_lineno
                    extracted_code = "\n".join(lines[start:end])
                    break
        
        if extracted_code:
            return f"=== Source: {fqn} ===\n\n{extracted_code}"
        else:
            # Fallback: Return whole file if symbol extraction fails (e.g. module level constant)
            return f"=== File: {rel_path} (Symbol {target_name} not isolated) ===\n\n{content}"

    except Exception as e:
        return f"Error reading file: {e}"

if __name__ == "__main__":
    _load_index()
    mcp.run()
