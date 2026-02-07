# CLI Tools & Registry Automation

This directory contains standalone CLI scripts that orchestrate the repository and codebase intelligence generation for the ADK MCP server. 

## `manage_registry.py`

This is the primary automation tool used to manage the Codebase Knowledge Registry. It tracks specific remote git repositories (like `google/adk-python` and its samples), clones their relevant tags into a local `~/.mcp_cache/tmp_build` folder, mines API and co-occurrence statistics, builds the AI context index, and formally registers them into `registry.yaml`.

This script exposes three main subcommands depending on your workflow:

### 1. `update`
```bash
python tools/cli/manage_registry.py update
```
This is the **most common and user-friendly command**. It reaches out to GitHub (via `ls-remote --tags`) for every repository listed your `registry.yaml`. It presents you with an interactive terminal UI (using Questionary) showing you exactly which remote versions you are missing locally. You simply check the boxes of the versions you want, and it will iterate through and index them automatically.

### 2. `add-version`
```bash
python tools/cli/manage_registry.py add-version google/adk-python v1.24.1
```
This allows explicitly adding (or aggressively overwriting using `--force`) a single specific repository version to the index. If you need to debug a broken index generation step, or urgently pull a very specific commit/tag without waiting for the interactive UI sweep, use this command. 
*Note: The `update` UI essentially just loops over your checked boxes and calls `add-version` for each one under the hood.*

### 3. `check-updates`
```bash
python tools/cli/manage_registry.py check-updates
```
A lightweight read-only command. It prints a stylized terminal table comparing all locally indexed versions of your repositories against the live GitHub tags. It does not write to the registry or perform any heavy AST scans.
