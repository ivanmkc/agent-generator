# Answer Generator Architectures

This file documents the architectural designs of the Answer Generators used in the benchmark suite. It is used by the report generator to provide context for the AI analysis.

## gemini-cli:mcp_adk_agent_runner_ranked_knowledge

**Source Image:** `gemini-cli:mcp_adk_agent_runner_ranked_knowledge`

### Core Philosophy
A metric-driven, hybrid multi-agent architecture that utilizes a central Router to dispatch tasks to specialized experts (Coding vs. Knowledge) backed by a high-fidelity, MCP-integrated ranked knowledge index.

### Topology
Hierarchical Router-Gateway with Specialized Expert Agents

### Key Tool Chain
- `search_adk_knowledge` (Semantic/BM25 search against Ranked Knowledge Index)
- `inspect_adk_symbol` (Precise lookup of code symbols)
- `list_adk_modules` (Ranked browsing of API surface)
- PodmanModel (Container lifecycle)

### Architecture Overview
The system operates as a containerized Agent Generator. It employs a Router-Gateway pattern where an incoming request is first analyzed by a 'Router' agent. Based on intent, the request is dispatched to one of two primary sub-agent chains: the 'Implementation Planner' (Coding Expert) or the 'Single Step Solver' (Knowledge Expert). These experts leverage a custom Model Context Protocol (MCP) server to access a 'Ranked Knowledge Index' via specific tools. The entire lifecycle is wrapped in a rigorous benchmarking framework that executes agents in isolated containers.

### Variants
- **bm25 (Default):** Uses BM25/Hybrid search.
- **keyword:** Uses pure Keyword search (baseline).

### Call Hierarchy
```mermaid
graph TD
    User[User Request] --> Router[Router Agent]
    Router -->|Coding Intent| Planner[Implementation Planner]
    Router -->|Knowledge Intent| Solver[Single Step Solver]
    Planner --> Worker[Retrieval Worker]
    Solver --> Worker
    Worker -->|MCP Tool| MCP[search_adk_knowledge / inspect_adk_symbol]
    MCP --> Response[Response Generation]
```

## gemini-cli:base

### Core Philosophy
A lightweight, asynchronous wrapper designed to expose local system CLI execution and file system access via a RESTful HTTP interface.

### Topology
Client-Server (REST API Gateway Pattern)

### Key Tool Chain
- Python 3 / FastAPI / Uvicorn
- Gemini CLI (Native)

### Architecture Overview
The architecture functions as a bridge between HTTP clients and the local operating system. It utilizes FastAPI to define a lightweight server that intercepts network requests and translates them into local system actions. The design relies heavily on Python's `asyncio` library to perform non-blocking subprocess execution, allowing the server to spawn shell commands (specifically the `gemini` CLI) and capture their `stdout` and `stderr` without halting the web server's event loop.

### Call Hierarchy
```mermaid
graph TD
    Client[External Client] -->|HTTP POST JSON| API[FastAPI Entry Point]
    API -->|Route: /| Exec[Command Execution]
    Exec -->|Validate 'gemini'| AsyncLoop[Asyncio Event Loop]
    AsyncLoop -->|Spawn Subprocess| CLI[Gemini CLI Executable]
    CLI -->|Capture stdout/stderr| AsyncLoop
    AsyncLoop -->|Return JSON| API
```

## gemini-cli:adk-docs-ext

**Source:** `https://github.com/pierpaolo28/adk-docs-ext` (main branch)

### Core Philosophy
A documentation-centric environment designed to assist developers by providing access to ADK documentation tools.

### Architecture Overview
This image installs the standard `adk-docs-ext` extension. It likely provides tools or context injection related to the ADK documentation, serving as a baseline for the documentation-enhanced variants.

## gemini-cli:adk-docs-ext-starter

**Source:** `https://github.com/pierpaolo28/adk-docs-ext` (agent-starter-pack branch)

### Core Philosophy
A minimalist "Starter Pack" configuration.

### Architecture Overview
This variant is built from the `agent-starter-pack` branch. It likely represents a stripped-down or essential set of documentation tools, testing the model's performance with a lighter context load compared to the full documentation suite.

## gemini-cli:adk-docs-ext-llms

**Source:** `https://github.com/pierpaolo28/adk-docs-ext` (llms.txt branch)

### Core Philosophy
Optimized for Large Language Models using the `llms.txt` standard.

### Architecture Overview
This image includes the `llms.txt` file (or tools to read it), which is a standardized format for providing condensed, LLM-friendly documentation context. This variant tests the effectiveness of providing a curated, token-efficient context summary to the model.

## gemini-cli:adk-docs-ext-llms-full

**Source:** `https://github.com/pierpaolo28/adk-docs-ext` (llms-full.txt branch)

### Core Philosophy
Maximum context injection.

### Architecture Overview
This variant uses the `llms-full.txt` branch, implying a comprehensive, detailed dump of the ADK documentation in the `llms.txt` format. It tests the model's ability to handle and utilize a large context window populated with extensive domain knowledge, potentially at the cost of higher latency or "lost in the middle" effects.

## ADK_HYBRID_V47

### Core Philosophy
A specialized "Mixture of Experts" architecture that routes user requests to either a dedicated "Coding Expert" (implementation loop) or a "Knowledge Expert" (retrieval pipeline) to maximize performance on distinct task types.

### Topology
Hierarchical Router-Gateway with Specialized Expert Agents.

### Architecture Overview
The system employs a Router to analyze the incoming request.
- If **Knowledge**, it delegates to the Knowledge Expert, which uses hierarchical retrieval and shared history to answer questions.
- If **Coding**, it delegates to the Coding Expert, which uses an isolated iterative loop to plan, write, run, and verify code in a temporary workspace.

### Call Hierarchy
```mermaid
graph TD
    User[User Request] --> Router[Routing Delegator]
    Router --(Knowledge)--> KnowledgeExp[Knowledge Expert]
    Router --(Coding)--> CodingExp[Coding Expert]
    
    subgraph Knowledge Expert
    Retrieval --> Solver
    end

    subgraph Coding Expert
    Planner --> Verifier --> ImplementLoop
    end
```

## ADK_RANKED_V46

### Core Philosophy
A retrieval-augmented generation (RAG) agent that utilizes a pre-computed "ranked index" of the ADK codebase to perform efficient, hierarchical knowledge discovery before attempting to answer queries.

### Topology
Sequential Pipeline (Hierarchical Retrieval -> Single Step Solver -> JSON Formatter)

### Architecture Overview
The system operates in two distinct phases: Discovery and Solving. 
1. The **Retrieval Agent** explores the ADK API surface using a paginated "ranked index" (most used classes first). It saves relevant "seeds" (class names) to the session state.
2. The **Solver** uses the conversation history (including the retrieval steps and docstrings) to generate a comprehensive natural language response.
3. A **Post-Processor** ensures the final output adheres to the strict JSON schema required by the benchmark harness.

### Key Tool Chain
- `list_ranked_targets`: Browses a paginated list of ADK symbols ranked by usage/importance.
- `search_ranked_targets`: Performs keyword searches against the index.
- `inspect_fqn`: Retrieves detailed docstrings, class hierarchy, and members for a specific Fully Qualified Name.

### Call Hierarchy
```mermaid
graph TD
    User[User Request] --> Setup[Setup Agent]
    Setup --> Retrieval[Hierarchical Retrieval Agent]
    Retrieval --(List/Search/Inspect)--> Index[Ranked Index]
    Retrieval --(Save Seeds)--> Solver[Single Step Solver]
    Solver --(Raw Text)--> PostProc[Post-Processor]
    PostProc --(JSON)--> Final[Final Answer]
```