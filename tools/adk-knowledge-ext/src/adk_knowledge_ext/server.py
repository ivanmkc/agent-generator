import os
import logging
import yaml
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from .index import get_index
from .reader import SourceReader

# Configuration
DEFAULT_INDEX_PATH = "/app/data/ranked_targets.yaml"
DEFAULT_REPO_PATH = "/app/adk-python"

ADK_INDEX_PATH = Path(os.environ.get("ADK_INDEX_PATH", DEFAULT_INDEX_PATH))
ADK_REPO_PATH = Path(os.environ.get("ADK_REPO_PATH", DEFAULT_REPO_PATH))

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("adk_knowledge_ext")

# Initialize Server
mcp = FastMCP("adk-knowledge")
reader = SourceReader(ADK_REPO_PATH)

def _ensure_index():
    get_index().load(ADK_INDEX_PATH)

@mcp.tool()
def list_adk_modules(page: int = 1, page_size: int = 20) -> str:
    """
    Lists ranked ADK modules and classes. Use this to explore the API surface. 
    
    Args:
        page: Page number (1-based).
        page_size: Number of items per page.
    """
    _ensure_index()
    items = get_index().list_items(page, page_size)
    
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
    _ensure_index()
    top_matches = get_index().search(query, limit)
    
    if not top_matches:
        return f"No matches found for '{query}'."
        
    lines = [f"--- Search Results for '{query}' ---"]
    for score, item in top_matches:
        rank = item.get("rank", "?")
        fqn = item.get("id") or item.get("fqn") or item.get("name") or "unknown"
        type_ = item.get("type")
        summary = item.get("docstring", "No summary.")
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
    _ensure_index()
    target, suffix = get_index().resolve_target(fqn)
    
    if not target:
        return f"Symbol '{fqn}' not found in index."
        
    rel_path = target.get("file_path")
    if not rel_path:
        return f"No file path recorded for {target.get('fqn', 'unknown')}."
    
    # We pass the full target FQN (e.g. google.adk.Agent) and the suffix (e.g. run)
    target_fqn = target.get("id") or target.get("fqn") or target.get("name")
    return reader.read_source(rel_path, target_fqn, suffix)

@mcp.tool()
def inspect_adk_symbol(fqn: str) -> str:
    """
    Returns the full structured specification (signatures, docstrings, properties) for a symbol from the ranked index.
    This is the PREFERRED way to understand an API.
    
    Args:
        fqn: The Fully Qualified Name (e.g., 'google.adk.agents.llm_agent.LlmAgent').
    """
    _ensure_index()
    target, suffix = get_index().resolve_target(fqn)
    
    if not target:
        return f"Symbol '{fqn}' not found in index."
    
    output = yaml.safe_dump(target, sort_keys=False)
    
    if suffix:
        return f"Note: Symbol '{fqn}' is not explicitly indexed. Showing parent symbol '{target.get('id') or target.get('fqn')}'.\n\n{output}"
    
    return output

# Optional Execution Tool
try:
    from adk_agent_tool import run_adk_agent
    mcp.tool()(run_adk_agent)
    logger.info("Enabled 'run_adk_agent' tool.")
except ImportError:
    logger.info("'adk_agent_tool' not found. Execution capabilities disabled.")

def main():
    mcp.run()

if __name__ == "__main__":
    main()
