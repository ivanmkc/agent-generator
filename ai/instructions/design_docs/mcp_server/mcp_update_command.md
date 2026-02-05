# Design Doc: MCP Update Command

**Status:** Proposed
**Author:** Gemini CLI
**Created:** 2026-02-04

## Objective
Implement a `mcp update` command to synchronize local knowledge bases with their remote upstream sources and ensure the MCP server configuration is current.

## Problem Statement
Currently, users have no easy way to refresh their local clones of knowledge bases or update their indices when the upstream repository changes. They must manually delete the cache or re-run setup (which might not trigger a pull if the directory exists).

## Proposed Solution
Add a new command `mcp update [KB_ID_PATTERN]` to the `manage_mcp.py` CLI.

### Workflow

1.  **Discovery:**
    *   Scan installed IDE configurations (using `_get_existing_kbs_from_configs`) to find active Knowledge Bases.
    *   Filter by optional `KB_ID_PATTERN` (e.g., `google/*`).

2.  **Git Synchronization:**
    *   For each active KB, locate `~/.mcp_cache/<repo_name>/<version>`.
    *   Run `git fetch`.
    *   Check `git status`.
    *   If behind remote: `git pull --ff-only`.
    *   If dirty/conflict: Warn and skip.

3.  **Index Refresh:**
    *   If an `index_url` is defined, check if the remote index has changed (ETag/Last-Modified).
    *   Download the new index if available.

4.  **Configuration Check:**
    *   Verify IDE config validity.
    *   Ensure required environment variables (GITHUB_TOKEN, API Key) are present.

5.  **Output:**
    *   Display a summary table of updated, skipped, and up-to-date repositories.

## User Interface

```bash
$ mcp update
Checking 3 repositories...

1. google/adk-python@v1.20.0
   - Path: ~/.mcp_cache/adk-python/v1.20.0
   - Status: Already up to date.

2. my-org/private-repo@main
   - Path: ~/.mcp_cache/private-repo/main
   - Action: Pulling 5 new commits...
   - Result: ✅ Updated to abc1234

3. custom/fork@dev
   - Path: ~/.mcp_cache/fork/dev
   - ⚠️  Skipped: Working directory is dirty (local changes detected).

Update complete.
```

## Implementation Details
*   Extend `SourceReader` or add a `SourceUpdater` class to handle the git logic safely.
*   Reuse `manage_mcp.py` configuration parsing logic.
