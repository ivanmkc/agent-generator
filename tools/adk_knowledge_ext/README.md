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

## Troubleshooting & FAQ

### "This repository is not supported..." or "Knowledge index not found"
**Q: I thought the knowledge index was bundled?**
**A:** Yes, the server comes bundled with indices for all major supported repositories found in its `registry.yaml` at build time.
However, if you are targeting:
1.  A **custom/private repository** not in the official registry.
2.  A **new version** of a supported repository that wasn't included in the last build.

Then the server attempts to download the index at runtime. If this download fails (e.g. corporate firewall, offline), you will see this error.

**Fix:** Use the `--knowledge-index-url` flag to point to a local file or accessible URL.
```bash
uvx --from ... codebase-knowledge-mcp-manage setup ... --knowledge-index-url file:///path/to/local/index.yaml
```

### Technical FAQ

**Q: How does the server locate the correct knowledge index?**
**A:** The server employs a 3-tier lookup strategy:
1.  **Bundled Manifest:** It first checks `manifest.json` (generated at build time) to see if a pre-downloaded index exists for the target repo/version in the `data/indices/` directory.
2.  **Registry Lookup:** If not bundled, it checks `registry.yaml` to find a remote URL for the index.
3.  **Direct URL:** Finally, it checks if `TARGET_INDEX_URL` was manually provided via environment variables.

**Q: Where are repositories and indices stored?**
**A:**
- **Indices:** Bundled indices are in the package installation directory. Downloaded indices are cached in `~/.mcp_cache/indices/`.
- **Source Code:** Repositories are cloned (shallowly) to `~/.mcp_cache/repo/{version}/`. The server performs a partial clone where possible to save space and bandwidth.

**Q: How does `search_knowledge` work?**
**A:** It defaults to **BM25 (sparse retrieval)** using the `rank_bm25` library, which is fast and requires no external API keys.
If you provide `GEMINI_API_KEY`, it automatically upgrades to a **Hybrid Search** (BM25 + Vector Embedding) for better semantic understanding.

**Q: Is it safe to use with private repositories?**
**A:** Yes.
- The server runs locally on your machine.
- It uses your local `git` credentials to clone repositories (so if you have access, it has access).
- No code is sent to any external server *unless* you enable semantic search (in which case, search queries are sent to the embedding API, but source code remains local).

---

## How to Use

Once installed, the tools are available to your AI agent. You can trigger them using natural language.

### 1. Explore the Codebase
> "List the top-level modules in this repo."
> "Show me the classes in the `core` module."

### 2. Search for Concepts
> "Search for where we handle 'authentication' logic."
> "Find code related to 'rate limiting'."

### 3. Read & Analyze Code
> "Read the source code for `auth.login` and explain how it works."
> "Inspect the `User` class definition."

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