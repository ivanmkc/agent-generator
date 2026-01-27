# MCP ADK Agent Runner (Smart Search)

## Core Philosophy
An enhanced execution environment equipped with active research tools, enabling the agent to "Google" the codebase (via pydoc/grep) during generation. This tests the model's ability to self-correct and perform on-the-fly learning.

## Topology
Tool-Augmented Execution Environment

## Key Tool Chain
- `pydoc` (Documentation Generator)
- `grep` / `find` (Source Browsing)
- `inspect` (Python Introspection)

## Architecture Overview
Unlike the Basic runner, this environment provides a suite of "Discovery Tools" to the agent.
- `search_docs(query)`: Wraps `pydoc -k` to find modules.
- `read_source(module)`: Returns the source code of a module.
- `get_signature(symbol)`: Returns the call signature.
This allows the agent to verify its assumptions about the API before writing code, drastically reducing hallucination rates for uncommonly used features.

## Key Components
| Component Name | Responsibility |
|----------------|----------------|
| `DiscoveryTools` | A class exposing introspection methods as LLM tools. |
| `AgentRunner` | Loops through generation and verification, allowing tool use. |
