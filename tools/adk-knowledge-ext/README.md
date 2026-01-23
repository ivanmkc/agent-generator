# ADK Knowledge Extension (`adk-knowledge-ext`)

A Gemini CLI extension that provides advanced knowledge retrieval and execution tools for the Agent Development Kit (ADK).

## Features

- **Ranked Knowledge Browsing**: `list_adk_modules` to explore the API surface by importance.
- **Semantic Search**: `search_adk_knowledge` using BM25 or keyword matching.
- **Deep Code Inspection**: 
    - `inspect_adk_symbol`: View structured specs (docs, signatures, properties).
    - `read_adk_source_code`: Read implementation source code, supporting nested classes and methods.
- **Agent Execution (Optional)**: `run_adk_agent` to execute ADK agents (requires `adk_agent_tool` in path).

## Installation

```bash
gemini extensions install ./tools/adk-knowledge-ext
```

## Configuration

The extension uses Environment Variables for configuration:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ADK_INDEX_PATH` | Path to `ranked_targets.yaml` | `/app/data/ranked_targets.yaml` |
| `ADK_REPO_PATH` | Path to ADK source root | `/app/adk-python` |
| `ADK_SEARCH_PROVIDER` | Search algo (`bm25` or `keyword`) | `bm25` |

## Usage

Once installed, the tools are automatically available to the Gemini agent.

**Example Session:**
> "How do I create a sequential agent?"
> -> Agent calls `search_adk_knowledge("sequential agent")`
> -> Agent calls `read_adk_source_code("google.adk.agents.sequential_agent.SequentialAgent")`
