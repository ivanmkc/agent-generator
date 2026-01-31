# Codebase Knowledge MCP Server

A repository-agnostic MCP server that gives AI coding agents (Claude Code, Cursor, Gemini CLI, Windsurf, etc.) deep access to any codebase.

## Tools Provided

- `list_modules(page)`: Lists ranked modules and classes in the codebase.
- `inspect_symbol(fqn)`: Shows the full spec (signatures, docstrings) of a symbol.
- `read_source_code(fqn)`: Reads implementation code directly from the Git repository.
- `search_knowledge(queries)`: Semantic search using concepts or keywords.

---

## Installation & Setup (Recommended)

The easiest way to configure this server in your preferred AI tool is using the built-in setup manager.

**Standard Setup:**
```bash
uvx --from "git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext" codebase-knowledge-mcp-manage setup
```

**Bypass Private Registry Auth (Common Fix):**
If you encounter "Connection closed" or 401 Unauthorized errors during setup, use a public index:
```bash
uvx --from "git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext" \
  codebase-knowledge-mcp-manage setup \
  --repo-url https://github.com/google/adk-python.git \
  --index-url https://pypi.org/simple \
  --force
```

**Restricted Environments (Manual Knowledge Index):**
If the server fails to download the knowledge index (e.g., "URL missing or failed" or corporate firewall blocks GitHub Raw), you can manually specify the index URL or a local file path:

1. Download the index YAML manually (contact repo owner for URL).
2. Run setup pointing to the file:
```bash
uvx --from "git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext" \
  codebase-knowledge-mcp-manage setup \
  --repo-url https://github.com/google/adk-python.git \
  --knowledge-index-url file:///path/to/downloaded/index.yaml \
  --force
```

The tool will:
1. Detect installed agents (Claude Code, Gemini CLI, Cursor, Windsurf, Roo Code, etc.).
2. Prompt for your **Target Repository URL** and **Version**.
3. Automatically update the appropriate configuration files.

> **Verified by:** `tests/integration/managed_setup/` (CLI tools) and `tests/integration/managed_json_setup/` (JSON-based IDEs).

---

## Uninstallation

To remove the configuration from your tools:

```bash
uvx --from "git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext" codebase-knowledge-mcp-manage remove
```

---

## Manual Configuration

Add the following to your MCP configuration file (e.g., `~/.gemini/settings.json`, `~/.cursor/mcp.json`, or Claude Desktop's `config.json`):

```json
{
  "mcpServers": {
    "codebase-knowledge": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext",
        "codebase-knowledge-mcp"
      ],
      "env": {
        "TARGET_REPO_URL": "https://github.com/your-org/your-repo.git",
        "TARGET_VERSION": "main",
        "GEMINI_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

### Configuration Options

| Variable | Description | Default |
| :--- | :--- | :--- |
| `TARGET_REPO_URL` | **Required.** The Git URL of the codebase to clone. | None |
| `TARGET_VERSION` | The branch or tag to use. | `main` |
| `TARGET_INDEX_URL` | URL to the index file. **Optional** for known repos. | Registry Lookup |
| `GEMINI_API_KEY` | Optional API Key for semantic/hybrid search features. | None |

> **Verified by:** `tests/integration/manual_uvx/`.

---

## Client Integration Tips

### Gemini CLI
The server generates a dynamic `INSTRUCTIONS.md` file tailored to your repository. You can instruct the Gemini CLI to use this as its system prompt by adding `GEMINI_SYSTEM_MD` to your environment:

```json
"env": {
  "GEMINI_SYSTEM_MD": "~/.mcp_cache/instructions/your-repo-name.md"
}
```

### General AI Agents
For other clients, we recommend adding this to your project's instructions:
> Use the `codebase-knowledge` tools to explore the API. Always `list_modules` first to see entry points, then `inspect_symbol` to verify signatures before writing code.

---

## Performance & Caching
*   **Environments:** `uvx` caches the Python environment for near-instant startup.
*   **Repository Data:** Cloned repositories and indices are cached in `~/.mcp_cache/`.

> **Verified by:** `tests/integration/registry_lookup/` and `tests/integration/resilience_*/`.