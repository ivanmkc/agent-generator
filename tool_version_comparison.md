# Tool Version Comparison

## Gemini CLI
- **Version:** `0.21.0-nightly.20251218.739c02bd6`
- **Source:** `../gemini-cli/package.json`
- **Key Tools:**
    - `ReadFile` (Truncation, BOM support)
    - `Edit` (Diff-based, partial replacement)
    - `WriteFile` (Overwrite)
    - `RunShellCommand`

## ADK Agents (`AdkTools`)
- **Version:** Custom Implementation (internal)
- **Status:** Parity with `gemini-cli` v0.21.0 features in progress.
- **Implemented:**
    - `read_file` (Added truncation & limits matching `gemini-cli`)
    - `write_file` (Overwrite only)
    - `run_shell_command`
- **Missing / Different:**
    - **Missing:** `replace_text` / `edit` (Partial replacement). Currently relies on full file overwrite via `write_file`.
    - **Difference:** ADK tools are Python-based and injected directly into the agent loop, whereas Gemini CLI tools are TypeScript-based and accessed via MCP or internal APIs.

## Recommendation
Implement `replace_text` in `AdkTools` to achieve functional parity with Gemini CLI's `Edit` tool, as identified in `gemini_cli_vs_adk_codewriting.md`.
