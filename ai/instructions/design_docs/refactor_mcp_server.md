# Refactoring MCP Server to Standalone Extension (`adk-knowledge-ext`)

## Objective
Extract the advanced Knowledge Retrieval and Agent Execution logic currently embedded in `benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner_ranked_knowledge` into a standalone, importable Python package named `adk-knowledge-ext`.

**Note:** We are naming this `adk-knowledge-ext` to differentiate it from the existing community extension `adk-docs-ext`, which primarily serves static `llms.txt` documentation. This new extension provides dynamic search, symbol inspection, and source code reading backed by a ranked index.

## Goals
1.  **Decouple from Docker**: The server should run independently of the specific benchmark Docker image, enabling local development and usage.
2.  **Configurable**: Paths to the ADK repository and the Knowledge Index must be configurable via Environment Variables (`ADK_REPO_PATH`, `ADK_INDEX_PATH`).
3.  **Installable**: Package it as a standard Python project (using `uv` or `pip`) compliant with Gemini CLI extension standards.
4.  **Modularity**:
    - Separate "Search" logic (BM25/Keyword) from "Server" logic.
    - Make "Agent Execution" (`run_adk_agent`) an optional feature, enabled only if dependencies are met.

## Current State vs. Future State

| Feature | Current (`adk_knowledge_mcp.py`) | Future (`adk-knowledge-ext`) |
| :--- | :--- | :--- |
| **Location** | Embedded in Benchmark Docker context | Standalone package in `tools/adk-knowledge-ext` |
| **Config** | Hardcoded `/app/...` paths | Env Vars: `ADK_INDEX_PATH`, `ADK_REPO_PATH` |
| **Search** | Hardcoded BM25 check | Pluggable `SearchProvider` (BM25, Keyword) |
| **Execution**| Hard dependency on `adk_agent_tool` | Optional dependency (try-import) |
| **Install** | `COPY` in Dockerfile | `gemini extensions install ./tools/adk-knowledge-ext` |

## Proposed Architecture

### Directory Structure
We will create the directory `tools/adk-knowledge-ext` with the following structure:

```text
tools/adk-knowledge-ext/
├── pyproject.toml         # Build config & dependencies (mcp, pyyaml, rank-bm25)
├── README.md              # Installation & Config guide
├── gemini-extension.json  # Gemini CLI extension manifest
└── src/
    └── adk_knowledge_ext/
        ├── __init__.py
        ├── server.py      # Main FastMCP entry point & tool registration
        ├── search.py      # SearchProvider abstraction & implementations (BM25, Keyword)
        ├── index.py       # Singleton Index loader & manager
        └── utils.py       # Path resolution helpers
```

### Configuration (Environment Variables)

| Variable | Description | Default (if not set) |
| :--- | :--- | :--- |
| `ADK_INDEX_PATH` | Path to `ranked_targets.yaml` | `/app/data/ranked_targets.yaml` (Docker compat) |
| `ADK_REPO_PATH` | Path to ADK library source root | `/app/adk-python` (Docker compat) |
| `ADK_SEARCH_PROVIDER` | Search algorithm to use | `bm25` |

### Tool Set
1.  **`list_adk_modules(page, page_size)`**: Browse the ranked index.
2.  **`search_adk_knowledge(query, limit)`**: Full-text search over the index.
3.  **`inspect_adk_symbol(fqn)`**: specific metadata lookup.
4.  **`read_adk_source_code(fqn)`**: Read file content from disk (requires `ADK_REPO_PATH`).
5.  **`run_adk_agent(...)`** *(Optional)*: Registered only if `adk_agent_tool` is importable.

## Implementation Plan

1.  **Scaffold Project**:
    - Create `tools/adk-knowledge-ext`.
    - Create `pyproject.toml` with `rank-bm25` as a dependency.
    - Create `gemini-extension.json` pointing to the local package.

2.  **Refactor Code**:
    - **`search.py`**: Isolate `BM25SearchProvider` and `KeywordSearchProvider`.
    - **`index.py`**: Create a robust `KnowledgeIndex` class that handles loading `yaml` and initializing the search provider.
    - **`server.py`**: Implement the `FastMCP` server, referencing `KnowledgeIndex`. Use `try-except` to conditionally register `run_adk_agent`.

3.  **Verification**:
    - Install locally: `gemini extensions install tools/adk-knowledge-ext`.
    - Configure local env vars pointing to the repo's `adk-python` and `ranked_targets.yaml`.
    - Run `gemini` and test `search_adk_knowledge`.

4.  **Docker Integration**:
    - Update the benchmark Dockerfile to copy this directory and install it.
    - Keep the existing `ENV` setup in Docker to ensure backward compatibility.