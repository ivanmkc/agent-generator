# Design Doc: Multi-Version Registry Architecture

**Status:** Proposed
**Author:** AI Agent
**Date:** Feb 4, 2026
**Based on:** `REGISTRY_PROPOSAL.md`

## 1. Overview

The current "Codebase Knowledge" MCP server uses a flat registry (e.g., `adk-python-v1.20.0`) which maps a unique ID directly to a repository URL and knowledge index. While simple, this architecture scales poorly as we support multiple versions of the same library (e.g., `v1.20.0`, `v1.23.0`) and makes it difficult to automate updates.

This document proposes a hierarchical, repo-centric registry architecture that supports versioning, automated lifecycle management, and compact instruction injection.

## 2. Problem Statement

1.  **Redundancy:** Each version requires a full duplicate entry in `registry.yaml` (URL, description, etc.).
2.  **Discovery:** Users have to guess which version ID to use if the naming convention isn't strictly enforced.
3.  **Instruction Bloat:** Injecting a flat list of 10 versions of the same library into the LLM's system prompt consumes excessive tokens.
4.  **Manual Maintenance:** There is no automated way to check for new tags or generate indices for them.

## 3. Proposed Solution

### 3.1 Hierarchical Schema

We transition `registry.yaml` to a structure grouped by repository.

```yaml
repositories:
  # Canonical Key: owner/repo
  google/adk-python:
    description: "Google Agent Development Kit (ADK) for Python"
    repo_url: "https://github.com/google/adk-python.git"
    
    # Default version to use if user requests 'google/adk-python' without version
    default_version: "v1.23.0"
    
    versions:
      v1.23.0:
        index_url: "https://storage.googleapis.com/.../indices/adk-python-v1.23.0.yaml"
        # Optional: override description for major version changes
        # description: "ADK v1.23.0 (New Event Loop)"
      
      v1.20.0:
        index_url: "https://storage.googleapis.com/.../indices/adk-python-v1.20.0.yaml"
```

### 3.2 KB ID Standard

We adopt a package-manager style syntax: `owner/repo@version`.

| Input ID | Resolution Logic |
| :--- | :--- |
| `google/adk-python@v1.23.0` | Exact match. |
| `google/adk-python` | Resolves to `default_version` (`v1.23.0`). |
| `adk-python-v1.20.0` | (Legacy) Mapped via alias or setup migration. |

### 3.3 CLI Workflow (`tools/manage_registry.py`)

A new tool will automate the lifecycle.

**Command: `check-updates`**
Scans all repositories in `registry.yaml`, queries `git ls-remote --tags`, and reports versions present in git but missing from the registry.

**Command: `add-version <repo_id> <version>`**
1.  **Clone:** `git clone --branch <version> ...` to `~/.mcp_cache/tmp/...`
2.  **Index:** Run `target_ranker` to generate `ranked_targets.yaml`.
3.  **Upload/Bundle:** Save the index to `data/indices/` or upload to cloud storage.
4.  **Update YAML:** append the new version entry to `registry.yaml`.

## 4. Instruction Strategy (Compact Injection)

Instead of listing every KB ID, we inject a summarized view into `INSTRUCTIONS.md`.

**Template:**
```markdown
**KNOWLEDGE BASE REGISTRY:**
(Format: `kb_id` | Description | Supported Versions)

*   `google/adk-python` | Google Agent Development Kit (ADK) for Python
    *   Versions: `v1.23.0` (default), `v1.20.0`
    *   *Usage:* `list_modules(kb_id="google/adk-python@v1.23.0", ...)`
```

**Benefits:**
- **Token Efficiency:** Description is repeated once per repo, not per version.
- **Clarity:** LLM understands the relationship between versions.

### 4.1 Version Constraints

To prevent agent confusion and hallucination, **only one version of a given repository can be loaded at a time.**
- If the configuration requests multiple versions of the same `owner/repo`, the server startup must fail or warn.
- The `setup` CLI should enforce this validation during the selection phase.

## 5. Alternate Proposals Considered

### 5.1 Status Quo (Flat Registry)
*   **Pros:** Simplest parsing logic.
*   **Cons:** Unmanageable list length; no clear "latest" vs "stable" distinction.
*   **Verdict:** Rejected for scalability reasons.

### 5.2 Dynamic Git Tags
*   **Concept:** The MCP server queries git tags at runtime and allows `google/adk-python@<any_tag>`.
*   **Pros:** Zero registry maintenance.
*   **Cons:**
    *   **Latency:** `git clone` on every new version request is slow.
    *   **No Index:** We can't serve a `ranked_targets.yaml` index for arbitrary tags without running the expensive ranker at runtime.
    *   **Reliability:** Depends on external git connectivity.
*   **Verdict:** Rejected. We need pre-computed indices for performance.

## 6. Implementation Plan

### Phase 1: Schema Migration
1.  Create `registry_v2.yaml` with the new structure.
2.  Update `manage_mcp.py` to read `v2` and fallback to `v1`.
3.  Update `server.py` to parse `@` syntax.

### Phase 2: Automation Tooling
1.  Implement `tools/manage_registry.py`.
2.  Create CI job to run `check-updates` weekly.

### Phase 3: Instruction Optimization
1.  Update `manage_mcp.py` to generate the compact instruction format from the v2 registry.
2.  Verify LLM performance with the new format.
