# Codebase Knowledge MCP Server

The **Codebase Knowledge MCP Server** is a high-performance [Model Context Protocol](https://modelcontextprotocol.io/) server designed to give AI agents deep, grounded, and efficient access to massive repositories. It provides a specialized toolset including:
- `list_modules(page, kb_id=None)`: Lists ranked modules and classes in the codebase.
- `inspect_symbol(fqn, kb_id=None)`: Shows the full spec (signatures, docstrings) of a symbol.
- `read_source_code(fqn, kb_id=None)`: Reads implementation code directly from the local clone.
- `search_knowledge(queries, kb_id=None)`: Semantic search using concepts or keywords.

## The Problem
Modern LLMs have large context windows, but they still struggle with:
1.  **Context Overload:** Shoving an entire codebase into context is expensive, slow, and often results in the model "getting lost" or hallucinating.
2.  **Noise:** Most files in a repo are irrelevant to a specific task. Finding the "high-value" entry points (classes, main functions, core modules) is difficult for an agent without guidance.
3.  **Stale Knowledge:** Standard RAG (Retrieval-Augmented Generation) often lacks the structural understanding of codebases (e.g., distinguishing a core interface from a test helper).

## The Solution
This server implements a **Ranked Retrieval** strategy. It uses pre-computed indices that rank symbols and modules based on their importance and centrality in the codebase. This allows agents to:
- **Browse First:** Explore the "top 20" most important modules instead of staring at thousands of files.
- **Inspect Deeply:** Retrieve full class specifications and signatures with zero noise.
- **Zero Latency:** High-value indices are bundled directly into the server for near-instant startup and offline use.

---

## Installation & Setup (Recommended)

The easiest way to configure this server is using the built-in setup manager.

**Standard Setup:**
```bash
uvx --from "git+https://github.com/ivanmkc/agent-generator.git@mcp_server#subdirectory=tools/adk_knowledge_ext" \
  codebase-knowledge-mcp-manage setup \
  --kb-ids "adk-python-v1.20.0"
```

**Non-Interactive (CI/CD):**
To skip prompts and use default settings:
```bash
uvx --from ... codebase-knowledge-mcp-manage setup \
  --kb-ids "adk-python-v1.20.0" \
  --quiet
```

The tool will:
1. Detect installed agents (Claude Code, Gemini CLI, Cursor, Antigravity).
2. Generate a custom `instructions/KNOWLEDGE_MCP_SERVER_INSTRUCTION.md` file.
3. Automatically update the agent's configuration with the necessary JSON state.

---

## Configuration

The server is configured via the `MCP_KNOWLEDGE_BASES` environment variable, which accepts a JSON array of knowledge base definitions.

### Example `settings.json` (Gemini CLI)

```json
{
  "mcpServers": {
    "codebase-knowledge": {
      "command": "uvx",
      "args": ["--from", "adk-knowledge-ext", "codebase-knowledge-mcp"],
      "env": {
        "MCP_KNOWLEDGE_BASES": "[{\"repo_url\": \"https://github.com/google/adk-python.git\", \"version\": \"v1.20.0\", \"index_url\": null}]",
        "ADK_SEARCH_PROVIDER": "bm25"
      }
    }
  },
  "context": [
    ".gemini/instructions/KNOWLEDGE_MCP_SERVER_INSTRUCTION.md"
  ]
}
```

### Configuration Options

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MCP_KNOWLEDGE_BASES` | **Required.** JSON string defining one or more repositories. | `[]` |
| `ADK_SEARCH_PROVIDER` | Search backend: `bm25` (default), `vector`, or `hybrid`. | `bm25` |
| `GEMINI_API_KEY` | Required for `vector` or `hybrid` search. | None |

---

## How It Works: The Knowledge Lifecycle

### 1. Build-Time Bundling
When the package is built (or installed via `uvx`), officially supported indices defined in `registry.yaml` are bundled directly into the Python package. This ensures **zero-latency startup** and **offline capability** for known repositories like `google/adk-python`.

### 2. Runtime Resolution
When a tool is called:
1.  **Check Registry:** The server looks for a locally bundled index matching the `repo_url` and `version` in `registry.yaml`.
2.  **Check Cache:** If not bundled, it checks `~/.mcp_cache/indices/`.
3.  **On-Demand Download:** If missing, it attempts to download the index from the `index_url` provided in the configuration.
4.  **Local Clone:** The server maintains a shallow clone of the source code in `~/.mcp_cache/repo/` for the `read_source_code` tool.

---

## Development & Testing

### Running Integration Tests
```bash
.venv/bin/python tools/adk_knowledge_ext/tests/integration/run_integration_tests.py
```

### Verifying Docker Runners
```bash
pytest benchmarks/tests/integration/test_unified_generators.py -k "ranked_knowledge"
```