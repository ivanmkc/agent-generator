# ADK Knowledge Extension

This package provides an MCP (Model Context Protocol) server that gives LLMs deep access to the Google ADK codebase. It allows agents to:
- **List** ranked modules and classes to discover APIs.
- **Inspect** detailed signatures and docstrings (via pre-computed index).
- **Read** source code directly from disk for deep implementation details.
- **Search** the knowledge base using keywords or concepts.

## Prerequisites

1.  **Install the package:**
    ```bash
    pip install .
    ```
    This installs the `adk-knowledge-mcp` command.

2.  **Prepare Data:**
    The server requires two data sources:
    *   `ranked_targets.yaml`: The pre-computed API index.
    *   `adk-python`: A clone of the ADK repository.

    By default, the server expects these in `/app/data` (Docker). For local use, you must set environment variables:
    *   `ADK_INDEX_PATH`: Path to `ranked_targets.yaml`.
    *   `ADK_REPO_PATH`: Path to the root of the `adk-python` repo.

## Installation

### Method 1: Modify `settings.json` (Manual)

You can manually configure your Gemini CLI (or any MCP client) by editing `~/.gemini/settings.json`.

Add the following to the `mcpServers` object:

```json
{
  "mcpServers": {
    "adk-knowledge": {
      "command": "adk-knowledge-mcp",
      "args": [],
      "env": {
        "ADK_INDEX_PATH": "/absolute/path/to/ranked_targets.yaml",
        "ADK_REPO_PATH": "/absolute/path/to/adk-python"
      }
    }
  }
}
```

*Note: Replace `/absolute/path/to/...` with the actual paths on your system.*

### Method 2: Install as a Gemini CLI Extension

You can install this tool as a packaged extension using `gemini-extension.json`.

1.  **Download/Locate `gemini-extension.json`:**
    This file is included in the root of this directory.

2.  **Customize Paths:**
    Open `gemini-extension.json` and verify the `env` paths. The default configuration assumes you have placed the data in `~/.adk/`.
    
    ```json
    "env": {
      "ADK_INDEX_PATH": "${HOME}/.adk/ranked_targets.yaml",
      "ADK_REPO_PATH": "${HOME}/.adk/adk-python"
    }
    ```

3.  **Install:**
    (Depending on how your `gemini-cli` supports extension loading, you might symlink this file or reference it directly. See `gemini-cli` documentation for `load_extension` or similar commands if available, or simply copy the `mcpServers` block from this file into your settings.)

    *Currently, the standard way is to merge the JSON configuration as shown in Method 1, but `gemini-extension.json` serves as a shareable definition for future package managers.*