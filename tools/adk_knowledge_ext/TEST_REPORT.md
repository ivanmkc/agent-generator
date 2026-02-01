# Test Report: Codebase Knowledge MCP Server

**Date:** 2026-02-01
**Status:** ✅ ALL TESTS PASSED

## Summary
Refactoring of the `manage_mcp` CLI, `server` error handling, and **Index Bundling** is complete.
- **Fixed:** `uvx` installation issues in restricted environments (added `--index-url`).
- **Fixed:** "Repo not supported" errors are now descriptive and actionable.
- **Fixed:** Case-insensitive `y/n` prompts in `manage_mcp` setup/remove.
- **Fixed:** Added robust file logging to `~/.mcp_cache/logs/`.
- **Feature:** **Auto-bundling of indices** during build time based on `registry.yaml`.
    - Supports multiple repositories.
    - Uses nested structure `indices/{repo_hash}/{version}.yaml` to avoid collisions.
    - Uses `manifest.json` for fast runtime lookup.
- **Verified:** Integration tests cover all scenarios including the new bundling logic.

## Test Execution Log (Latest Run)

```text
--- Starting Bundled Index Verification ---
Server Initialized.
Calling list_modules...
Tool Output: --- Ranked Modules (Page 1) ---
[?] class: bundled.symbol
SUCCESS: Loaded bundled index correctly.
PASSED
```

## Scenarios Covered

| Test Suite | Scenario | Status | Notes |
|------------|----------|--------|-------|
| `bundled_index` | **NEW** Build-time Bundling | ✅ PASS | Verified `hatch_build.py` manifest generation & server loading. |
| `manual_uvx` | Manual `uvx` execution | ✅ PASS | Verified basic connectivity. |
| `extension_uvx` | Extension-style install | ✅ PASS | Verified `install_extension.py` simulation. |
| `resilience_invalid_version` | Invalid Repo Version | ✅ PASS | Graceful fallback to error message. |
| `resilience_missing_index` | Missing Index File | ✅ PASS | Graceful fallback to error message. |
| `resilience_no_api_key` | Missing API Key | ✅ PASS | Fallback to BM25 search. |
| `registry_lookup` | Registry URL Resolution | ✅ PASS | Correctly resolves index URL from `registry.yaml`. |
| `registry_miss` | Unknown Repository | ✅ PASS | Returns actionable "Not Supported" error. |
| `managed_setup` | CLI Integration (Gemini) | ✅ PASS | Verifies `mcp add` command generation. |
| `managed_json_setup` | JSON Integration (Cursor, etc.) | ✅ PASS | Verifies `mcp.json` modification. |
| `managed_claude` | Claude Integration | ✅ PASS | Verifies Claude-specific argument passing. |

## Key Changes Validated
1. **Bundling Architecture:** `hatch_build.py` now iterates `registry.yaml` and downloads ALL indices into a hashed directory structure, creating a `manifest.json`. `server.py` consults this manifest first.
2. **Error Messaging:** The server now explicitly tells users how to fix missing index errors.
3. **Logging:** Debug logs are written to `~/.mcp_cache/logs/codebase-knowledge.log`.
4. **Interactive Prompts:** `manage_mcp` uses a custom case-insensitive confirmation loop.
