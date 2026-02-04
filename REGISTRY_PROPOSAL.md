# Registry Restructuring & Automation Proposal

## 1. Current State Assessment
- **Current Version in Registry:** `v1.20.0`
- **Latest Available Version:** `v1.23.0` (as of Feb 4, 2026)
- **Problem:** The current flat registry (`adk-python-v1.20.0`) scales poorly with multiple versions and lacks a standardized update mechanism. Instructions are verbose if multiple versions of the same library are listed.

## 2. Proposed Schema (Hierarchical)

We will transition `registry.yaml` to a repo-centric hierarchy. This allows grouping versions under a single canonical repository definition.

### New `registry.yaml` Format
```yaml
repositories:
  google/adk-python:
    description: "Google Agent Development Kit (ADK) for Python"
    repo_url: "https://github.com/google/adk-python.git"
    default_version: "v1.23.0"
    versions:
      v1.23.0:
        index_url: "https://.../indices/adk-python-v1.23.0.yaml"
        # Optional: override description if major version changes significantly
      v1.20.0:
        index_url: "https://.../indices/adk-python-v1.20.0.yaml"
```

## 3. KB ID Standardization
We will adopt a standard package-manager style syntax for `kb_id`:

**Syntax:** `{owner}/{repo}@{version}`

**Examples:**
- `google/adk-python@v1.23.0`
- `google/adk-python@v1.20.0`

*Backward Compatibility:* The setup tool can map old flat IDs (e.g., `adk-python-v1.20.0`) to the new format if needed, but we should encourage the new syntax.

## 4. Compact Instruction Injection
Instead of listing every version as a separate entry in the LLM's system prompt, we will inject a grouped summary.

**Template Output:**
```markdown
**KNOWLEDGE BASE REGISTRY:**
(Format: `kb_id` | Description | Supported Versions)

*   `google/adk-python` | Google Agent Development Kit (ADK) for Python
    *   Versions: `v1.23.0` (default), `v1.20.0`
    *   *Usage:* `list_modules(kb_id="google/adk-python@v1.23.0", ...)`
```

This reduces token usage while keeping all versions discoverable.

## 5. Automated Update Workflow
We need a new CLI tool `tools/manage_registry.py` to handle lifecycle management.

### Workflow: `check-updates`
1.  **Scan:** Iterate through all repositories in `registry.yaml`.
2.  **Fetch:** Run `git ls-remote --tags <repo_url>` to get the list of remote tags.
3.  **Compare:** Parse semantic versions (ignoring beta/rc unless specified). Compare against keys in `versions`.
4.  **Report:** Output a list of missing versions (e.g., `v1.23.0`, `v1.22.1`).

### Workflow: `add-version`
A command to onboard a new version, which involves generating the knowledge index.

```bash
python tools/manage_registry.py add-version google/adk-python v1.23.0
```

**Steps:**
1.  **Clone:** Temporarily clone the repo at `v1.23.0`.
2.  **Index:** Run the ranking/indexing logic (e.g., `target_ranker`) to generate the `ranked_targets.yaml`.
3.  **Upload:** (Optional) Upload the index to the artifact store (or bundle it).
4.  **Update YAML:** Add the `v1.23.0` entry to `registry.yaml` with the new index path.

## 6. Git Cloning & Storage Strategy
The `SourceReader` logic will be updated to handle the new `kb_id` format.

**Storage Path:**
`~/.mcp_cache/{owner}/{repo}/{version}/`

**Example:**
`/Users/ivanmkc/.mcp_cache/google/adk-python/v1.23.0/`

This ensures cleanly isolated versions on disk.

## 7. Migration Plan
1.  **Refactor Registry:** Convert `registry.yaml` to the new hierarchical format.
2.  **Update Setup:** Modify `manage_mcp.py` to parse the new YAML and handle interactive selection (User selects Repo -> User selects Version(s)).
3.  **Update Server:** Update `server.py` and `reader.py` to parse `owner/repo@version` IDs.
4.  **Generate Indices:** Generate the index for `v1.23.0` (and `v1.22.1` etc. if desired).
