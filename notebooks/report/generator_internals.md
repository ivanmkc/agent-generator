# Generator Internals (Static Reference)

> This file describes the static architectures of the available generators. Runtime parameters (like Model) are injected during execution.

### GeminiCliPodman: gemini-cli:adk-docs-ext
- **Model:** `[Injected at Runtime]`
- **Docker Image:** `gemini-cli:adk-docs-ext`

**Environment:** **Documentation-Augmented Environment:** This environment is pre-configured with the `adk-docs-mcp` extension. 
*   **Tools:** Provides specialized tools (`fetch_docs`, `list_doc_sources`) via the **custom `adk-docs-mcp` server**. 
*   **Strategy:** RAG (Retrieval-Augmented Generation) against a static documentation index. It allows the model to look up API details before generating code but does not natively execute agent code for verification.

---

### GeminiCliPodman: gemini-cli:mcp_context7
- **Model:** `[Injected at Runtime]`
- **Docker Image:** `gemini-cli:mcp_context7`

**Environment:** **Context7 Semantic Search:** A specialized environment configured with the **`Context7` MCP server**. 
*   **Tools:** Relies on semantic retrieval tools provided by the `Context7` server to fetch relevant code snippets and documentation chunks based on query intent.

---

### GeminiCliPodman: gemini-cli:mcp_adk_agent_runner_basic
- **Model:** `[Injected at Runtime]`
- **Docker Image:** `gemini-cli:mcp_adk_agent_runner_basic`

**Environment:** **Baseline Agent Runner (Execution-Capable):** A streamlined execution environment designed to *run* ADK agents. 
*   **Tools:**
    *   **Built-in (gemini-cli):** `read_file`, `write_file`, `list_directory`.
    *   **Custom MCP:** `run_adk_agent` (provided by the **`mcp_adk_agent_runner` server**).
*   **Strategy:** "Code -> Run -> Fix". The model relies on its pre-trained knowledge to generate initial code, then uses the execution tool to verify behavior. It lacks specific tools for code exploration, making it dependent on internal knowledge for API correctness.

---

### GeminiCliPodman: gemini-cli:mcp_adk_agent_runner_smart_search
- **Model:** `[Injected at Runtime]`
- **Docker Image:** `gemini-cli:mcp_adk_agent_runner_smart_search`

**Environment:** **Smart Discovery Runner (Research & Execution):** An advanced environment that combines execution capabilities with deep code exploration tools.
*   **Tools:**
    *   **Built-in (gemini-cli):** `read_file`, `write_file`, `list_directory`.
    *   **Custom MCP:** `run_adk_agent`, `get_module_help` (pydoc), and `search_file_content` (grep) — all provided by the **enhanced `mcp_adk_agent_runner` server**.
*   **Strategy:** "Research -> Code -> Run -> Fix". Before generating code, the model is explicitly instructed (via system prompt) to use the custom research tools to verify import paths and class signatures. This "Mandatory Research Phase" grounds the model in the actual codebase state before execution attempts.

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
