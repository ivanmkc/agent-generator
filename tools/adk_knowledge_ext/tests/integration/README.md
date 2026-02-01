# Integration Tests Matrix

This directory contains a suite of integration tests designed to verify the Codebase Knowledge MCP server across various deployment scenarios, configurations, and failure modes. All tests run in isolated containers to simulate real-world usage.

## Test Matrix

| Category | Test Scenario | Description | Key Verification |
| :--- | :--- | :--- | :--- |
| **Lifecycle** | `full_lifecycle` | **End-to-End Workflow:** Simulates a user installing from source, setting up the tool, running it, and removing it. | • `uvx --local` installation<br>• Build-time index bundling<br>• `setup` & `remove` CLI commands<br>• Tool execution using bundled index |
| **Bundling** | `bundled_index` | **Build-Time Bundling:** Verifies the build hook downloads the external index and embeds it into the package artifact. | • Ensures final package is self-contained<br>• Verifies `data/indices/...` creation<br>• Confirms NO runtime downloads needed |
| **Core** | `manual_uvx` | **Direct Execution:** Runs the server manually via `uvx` with explicit environment variables. | • Server startup<br>• `list_modules` tool execution<br>• API key handling |
| **Core** | `extension_uvx` | **Extension Mode:** Simulates an IDE extension triggering the server discovery. | • Auto-configuration via env vars<br>• Index downloading (if not bundled) |
| **Setup** | `managed_setup` | **Gemini CLI Integration:** Verifies the `codebase-knowledge-mcp-manage` setup tool for Gemini. | • Registry lookup<br>• `settings.json` generation (CLI-based config) |
| **Setup** | `managed_json_setup` | **JSON Config Integration:** Verifies setup for IDEs using `mcp.json` (Cursor, Windsurf, etc.). | • `mcp.json` patching<br>• Correct argument formatting |
| **Setup** | `managed_claude` | **Claude Code Integration:** Verifies setup specifically for Claude's CLI. | • Separator-style arguments (`--` separation) |
| **Resilience** | `resilience_invalid_version` | **Version Mismatch:** Tests server behavior when the requested repo version doesn't match the index. | • Graceful warning/error message |
| **Resilience** | `resilience_missing_index` | **Missing Index:** Tests server behavior when no index URL is provided and no bundle exists. | • Actionable "TO FIX THIS" error message |
| **Resilience** | `resilience_no_api_key` | **Missing Credentials:** Tests behavior when Hybrid Search is requested but no API key is present. | • Clear error requiring API key<br>• Prevention of crash |
| `registry_miss` | `registry_miss` | **Unknown Repo:** Tests behavior when the target repo is not in the internal registry. | • Informative error about unsupported repo |

## Running Tests

To run the full suite:

```bash
python3 tools/adk_knowledge_ext/tests/integration/run_integration_tests.py
```

To run a specific test (e.g., `full_lifecycle`):

1. **Build the image:**
   ```bash
   podman build -t adk-test-lifecycle -f tools/adk_knowledge_ext/tests/integration/full_lifecycle/Dockerfile .
   ```

2. **Run the container:**
   ```bash
   podman run --rm adk-test-lifecycle
   ```
