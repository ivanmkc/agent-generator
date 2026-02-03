# Codebase Knowledge MCP - Development Plan

## 1. Historical Findings & Context
- **Branch Strategy:** The project is centered on the `mcp_server` branch.
- **Docker/Podman Build Flow:** 
    - The `remote_main` runner requires a private GitHub repository (`agent-generator`).
    - Successfully implemented a secure build flow using **Docker Secrets** (`--mount=type=secret`).
    - Standardized on using the local `.env` file as the secret source, which is automatically parsed by `podman_utils.py`.
- **Ranked Knowledge Index:**
    - The server requires pre-computed indices (YAML).
    - On-the-fly indexing is not yet supported, so the "Custom Repository" interactive option was removed to prevent broken configurations.
- **IDE Integration Logic:**
    - **Claude Code:** Uses `claude mcp add` (Standard CLI).
    - **Cursor:** Uses `~/.cursor/mcp.json` (Confirmed via docs).
    - **Windsurf:** Uses `~/.codeium/windsurf/mcp_config.json` (Confirmed via docs).
    - **Codex:** Uses `codex mcp add` (Confirmed via docs).
    - **Roo Code:** Discrepancy found. Official docs point to VS Code global storage (`.../globalStorage/rooveterinaryinc.roo-cline/...`), while our code uses `~/.roo-code/mcp.json`.

## 2. Finished Tasks
- [x] **Runner Modernization:** Removed redundant `git init` and `mkdir` commands from Dockerfiles.
- [x] **Secure Build Secrets:** Updated `podman_utils.py` and `remote_main` Dockerfile to support `.env` secret mounting.
- [x] **Multi-Repo Context:** Updated `KB_REGISTRY` format to `{kb_id: description}` as requested.
- [x] **UX Improvements:** Rephrased setup prompts as questions and ensured case-insensitivity.
- [x] **Integration Testing:** Verified both `ranked_knowledge` and `remote_main` runners pass the unified integration tests (6/6 passing).
- [x] **Documentation:** Updated all READMEs to point to the correct `mcp_server` branch and installation commands.
- [x] **Hygiene:** Cleaned up accidentally tracked large index files and unused `patch_settings.py`.

## 3. Current Status & Questions
- **Roo Code Accuracy:** The path `~/.roo-code/mcp.json` is likely incorrect for modern Roo Code installations. 
    - *Question:* Should we update this to the official VS Code global storage path?
- **Antigravity:** This integration is assumed correct as it shares logic with the verified Gemini CLI flow.

## 4. Upcoming Tasks
- [ ] **Fix Roo Code Path:** Update `IDE_CONFIGS` in `manage_mcp.py` to use the standard VS Code extension global storage path for Roo Code.
- [ ] **Verification:** Perform a final check of the generated `settings.json` and `instructions/*.md` files in a clean environment.
- [ ] **Final Push:** Ensure all local documentation and plan changes are pushed to `mcp_server`.

## 5. Reference Commands

### Building Docker Images
**Remote Main Runner (Requires `.env` with `GITHUB_TOKEN`):**
```bash
podman build --no-cache --secret id=github_token,src=.env -t gemini-cli:mcp_adk_agent_runner_remote_main -f benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner_remote_main/Dockerfile .
```

**Ranked Knowledge Runner (Local Build):**
```bash
podman build -t gemini-cli:mcp_adk_agent_runner_ranked_knowledge -f benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner_ranked_knowledge/Dockerfile .
```

### Running Integration Tests
**Run Both Ranked Knowledge & Remote Main:**
```bash
python -m pytest -v benchmarks/tests/integration/test_unified_generators.py -k "ranked_knowledge or remote_main"
```

**Run Specific Case:**
```bash
python -m pytest -v benchmarks/tests/integration/test_unified_generators.py -k "podman_mcp_adk_runner_remote_main_test_case"
```

### Verifying Output (Inside Container)
**Inspect Generated Instructions:**
```bash
podman run --rm gemini-cli:mcp_adk_agent_runner_remote_main cat /workdir/.gemini/instructions/adk-python.md
```
