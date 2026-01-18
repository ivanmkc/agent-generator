# Generator Internals (Static Reference)
> This file describes the static architectures of the available generators. Runtime parameters (like Model) are injected during execution.
### ADK_HYBRID_V47
- **Model:** `[Injected at Runtime]`

# Architecture Overview: Experiment 66 (V46)

### 1. Agent Topology
**Sequential Chain.** The system utilizes a `SequentialAgent` to execute a linear pipeline of specialized sub-agents. The flow is strictly unidirectional: Setup $\to$ Retrieval $\to$ Solver $\to$ Teardown.

### 2. Specialists
*   **Hierarchical Retrieval Agent:** Navigates a static "ranked targets" index (offline YAML) to locate relevant API symbols using pagination and inspection.
*   **Single Step Solver:** A logic-focused agent that consumes the retrieved conversation history to generate a natural language solution in a single turn.
*   **Supervisor Formatter:** An external, decoupled LLM call (Post-Processor) that converts the Solver's raw text into strict JSON schemas (e.g., `FixErrorAnswerOutput`) after the main agent chain completes.

### 3. Tools
Tools are exclusively enabled for the Retrieval Agent to query the ADK index:
*   `list_ranked_targets`: Browses a paginated list of ADK symbols ranked by usage/importance.
*   `search_ranked_targets`: Performs keyword searches against the index.
*   `inspect_fqn`: Retrieves detailed docstrings, class hierarchy, and members for a specific Fully Qualified Name.

### 4. Flow
Data persists via **Shared Session History**. The Retrieval Agent saves findings (seeds) to the session state. The Solver "reads" the upstream retrieval logs and inspection outputs to synthesize an answer. The raw text response is finally captured by the Orchestrator and mapped to JSON via the decoupled formatter.

---
