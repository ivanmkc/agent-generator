# Generator Internals (Static Reference)

> This file describes the static architectures of the available generators. Runtime parameters (like Model) are injected during execution.

### GeminiCliPodman: gemini-cli:adk-docs-ext
- **Model:** `[Injected at Runtime]`
- **Docker Image:** `gemini-cli:adk-docs-ext`

**Environment:** ADK Python development environment with documentation tools and extensions.

---

### GeminiCliPodman: gemini-cli:mcp_context7
- **Model:** `[Injected at Runtime]`
- **Docker Image:** `gemini-cli:mcp_context7`

**Environment:** Gemini CLI configured with Context7 (semantic search) MCP server.

---

### GeminiCliPodman: gemini-cli:mcp_adk_agent_runner_basic
- **Model:** `[Injected at Runtime]`
- **Docker Image:** `gemini-cli:mcp_adk_agent_runner_basic`

**Environment:** **Baseline Runner:** A minimal execution environment for ADK agents. It can load and run provided agent code but lacks intrinsic tools for code exploration or documentation lookup. It relies entirely on the model's pre-trained knowledge for API usage.

---

### GeminiCliPodman: gemini-cli:mcp_adk_agent_runner_smart_search
- **Model:** `[Injected at Runtime]`
- **Docker Image:** `gemini-cli:mcp_adk_agent_runner_smart_search`

**Environment:** **Smart Discovery Runner:** An enhanced environment equipped with active research tools (`pydoc_search`, `source_browser`). It enables the agent to dynamically look up library documentation and inspect source code *during* the generation loop, allowing it to correct hallucinations and find the right imports.

---

### ADK_Single_Agent_Generalist
- **Model:** `[Injected at Runtime]`

**Agent:** `workflow_solver` (Single Agent)

**System Instruction:**
> You are an expert software engineer tasked with solving programming benchmarks. You have access to a set of tools to read code, write files, and run commands. You are operating in a workspace at /var/folders/nh/n7l064rj4wx0z7jsyr5q4wtc00rmmq/T/adk_workflow_5wh10y1v. The ADK Python repository is avai...

---

### ADK_Multi_Agent_Index_Retrieval
- **Model:** `[Injected at Runtime]`

**Multi-Agent Workflow:** `setup_agent` → `prompt_sanitizer_agent` → `module_selector_agent` → `docstring_fetcher_agent` → `implementation_planner` → `verification_planner` → `implementation_loop` → `final_verifier` → `teardown_agent`

---

### ADK_Multi_Agent_Index_Retrieval_No_History
- **Model:** `[Injected at Runtime]`

**Multi-Agent Workflow:** `setup_agent` → `prompt_sanitizer_agent` → `module_selector_agent` → `docstring_fetcher_agent` → `implementation_planner` → `verification_planner` → `implementation_loop` → `final_verifier` → `teardown_agent`

---

### ADK_Multi_Agent_Tool_Retrieval
- **Model:** `[Injected at Runtime]`

**Multi-Agent Workflow:** `setup_agent` → `prompt_sanitizer_agent` → `module_selector_agent` → `implementation_planner` → `verification_planner` → `implementation_loop` → `final_verifier` → `teardown_agent`

---
