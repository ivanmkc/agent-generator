# MCP ADK Agent Runner (Basic)

## Core Philosophy
A minimal execution environment designed to serve as a baseline for benchmarking ADK agents. It strictly isolates the agent from external documentation or search tools, forcing reliance on the model's pre-trained knowledge.

## Topology
Single-Container Execution Environment

## Key Tool Chain
- Python 3.11+
- Google ADK (Agent Development Kit)
- Gemini CLI (Execution Wrapper)

## Architecture Overview
This runner provides a "clean slate" environment. It pre-installs the `google-adk` library but deliberately omits any discovery tools (like `pydoc` search or source browsers). This makes it ideal for testing "Hallucination Rates" on API usage—if the model doesn't know the API by heart, it will fail, providing a clear signal of parametric knowledge limits versus retrieval capabilities.

## Key Components
| Component Name | Responsibility |
|----------------|----------------|
| `adk-python` | The core library being tested. |
| `main.py` (CLI) | Entry point that accepts agent code and executes it. |
