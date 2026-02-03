# Gemini CLI Benchmark Runners

This directory contains Docker configurations for running ADK benchmarks with different MCP server setups.

## Variants

### 1. `mcp_adk_agent_runner_ranked_knowledge` (Default / Local Dev)
- **Use Case:** Validating local changes to the MCP server code.
- **Installation:** Bundles the local `tools/adk_knowledge_ext` directory into the image.
- **Configuration:** Uses `manage setup --local` to point the agent to the on-disk code.
- **Index:** Uses the index bundled within the package (`indices/adk-python-v1.20.0.yaml`).

### 2. `mcp_adk_agent_runner_remote_main` (CI / Release Test)
- **Use Case:** Verifying that the tool works when installed from the public GitHub repository (integration testing the "user flow").
- **Installation:** Installs from `git+https://github.com/ivanmkc/agent-generator.git@mcp_server#subdirectory=tools/adk_knowledge_ext`.
- **Configuration:** Uses `manage setup` (default) which configures `uvx --from git+...`.
- **Requirements:** Requires `uv` to be installed in the image.
- **Note:** This runner depends on the code being pushed to the remote `main` branch.

## Usage

These images are built and managed by the `GeminiCliPodmanAnswerGenerator` class in `benchmarks/answer_generators/gemini_cli_podman_answer_generator.py`.
