# Generator Internals (Static Reference)

> This file describes the static architectures of the available generators. Runtime parameters (like Model) are injected during execution.

### GeminiCliPodman: gemini-cli:mcp_adk_agent_runner_ranked_knowledge
- **Model:** `[Injected at Runtime]`
- **Docker Image:** `gemini-cli:mcp_adk_agent_runner_ranked_knowledge`

**Environment:** **Ranked Knowledge Runner (V47 Port):** This runner incorporates the high-fidelity 'Ranked Knowledge Index' from Experiment 67 (V47) directly into the Gemini CLI environment via a custom MCP server. It exposes `search_adk_knowledge` and `inspect_adk_symbol` tools, allowing the CLI agent to perform the same grounded retrieval as the Python-based sequential agent.

---

### GeminiCliPodman: gemini-cli:mcp_adk_agent_runner_remote_main
- **Model:** `[Injected at Runtime]`
- **Docker Image:** `gemini-cli:mcp_adk_agent_runner_remote_main`

**Environment:** **Remote Main Runner:** Tests the production flow where the MCP server is installed directly from the GitHub main branch using uvx.

---
