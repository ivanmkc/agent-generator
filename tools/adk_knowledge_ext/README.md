# Codebase Knowledge MCP Server

A repository-agnostic MCP server that gives LLMs deep access to any codebase. It allows agents to:
- **List** ranked modules and classes.
- **Inspect** detailed signatures and docstrings (via a pre-computed index).
- **Read** source code directly from Git repositories.
- **Search** the codebase using keywords or concepts.

## Installation (Recommended)

The standard way to use this server is via `uvx`. This method handles installation, environment isolation, and caching automatically.

Add the following configuration to your `~/.gemini/settings.json` file. The server will automatically download the search index and clone the repository the first time it runs.

```json
{
  "mcpServers": {
    "my-codebase": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext",
        "codebase-knowledge-mcp"
      ],
      "env": {
        "TARGET_REPO_URL": "https://github.com/google/adk-python.git",
        "TARGET_VERSION": "v1.20.0",
        "TARGET_INDEX_URL": "https://raw.githubusercontent.com/ivanmkc/agent-generator/main/benchmarks/generator/benchmark_generator/data/ranked_targets.yaml",
        "GEMINI_API_KEY": "YOUR_KEY_HERE" 
      }
    }
  }
}
```

### Performance & Caching
*   **Tools:** `uvx` caches the installed python environment, so subsequent runs start instantly.
*   **Data:** The server caches the cloned repository and downloaded index in `~/.mcp_cache/`, ensuring network efficiency.

## Configuration Options

You can customize the server behavior by modifying the `env` block in your settings file.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `TARGET_REPO_URL` | **Required.** The Git URL of the codebase to clone. | None |
| `TARGET_INDEX_URL` | **Required.** URL to the `ranked_targets.yaml` index file. | None |
| `TARGET_VERSION` | The branch or tag to use. | `main` |
| `GEMINI_API_KEY` | API Key for semantic search features. | None |
| `ADK_SEARCH_PROVIDER` | Search mode: `bm25` (local) or `hybrid` (semantic+local). | `bm25` |

## Manual Installation (Advanced)

If you prefer to manage your own Python environment or need offline capability by bundling data at install time:

```bash
# 1. Set build-time variables (optional, to bundle data)
export TARGET_INDEX_URL="https://example.com/index.yaml"

# 2. Install
pip install "git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext"

# 3. Run
export TARGET_REPO_URL="..."
codebase-knowledge-mcp
```