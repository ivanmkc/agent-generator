# ADK Knowledge Extension

This package provides an MCP (Model Context Protocol) server that gives LLMs deep access to the Google ADK codebase. It includes the necessary ADK source code and search index bundled directly within the package.

## Installation

Install directly from GitHub using `pip`. This command triggers a build hook that automatically clones the ADK repository and downloads the search index into the package, making it fully self-contained.

```bash
pip install "git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext"
```

*Note: The installation process may take a moment as it downloads the ADK repository.*

## Configuration

### Option A: Install via Extension File (Recommended)
Download the extension definition and load it (if your CLI supports it) or merge it manually.

```bash
curl -o gemini-extension.json \
  https://raw.githubusercontent.com/ivanmkc/agent-generator/main/tools/adk_knowledge_ext/gemini-extension.json
```

### Option B: Manual Configuration
Add the following to your `~/.gemini/settings.json` file under `mcpServers`.

```json
{
  "mcpServers": {
    "adk-knowledge": {
      "command": "adk-knowledge-mcp",
      "args": []
    }
  }
}
```

## Advanced Usage

If you wish to use a custom index or a local ADK checkout instead of the bundled one, you can set the following environment variables in your configuration:

*   `ADK_INDEX_PATH`: Path to a custom `ranked_targets.yaml`.
*   `ADK_REPO_PATH`: Path to a local clone of `adk-python`.