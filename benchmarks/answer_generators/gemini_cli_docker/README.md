# Gemini CLI Benchmark Runners

This directory contains Docker configurations for running ADK benchmarks with different MCP server setups.

## Variants

### 1. `mcp_adk_agent_runner_ranked_knowledge` (Default / Local Dev)
- **Use Case:** Validating local changes to the MCP server code.
- **Installation:** Bundles the local `tools/adk_knowledge_ext` directory into the image.
- **Configuration:** Uses `manage setup --local` to point the agent to the on-disk code.
- **Index:** Uses the index bundled within the package (`indices/adk-python-v1.20.0.yaml`).

### 2. `mcp_adk_agent_runner_remote_main` (CI / Release Test)
- **Use Case:** Simulates the remote installation flow but uses local code overrides for testing.
- **Installation:** Copies the local `tools/adk_knowledge_ext` directory into the image.
- **Configuration:** Uses `manage setup --local` to point to the copied extension.
- **Why this setup?** Typically, a "remote" runner would pull directly from GitHub (`uvx --from git+...`). However, to verify unmerged changes in CI or local development without pushing to a remote branch first, we inject the local source code while maintaining the "remote-style" structure (no pre-cloned repositories, relying on dynamic retrieval).
- **Requirements:** Requires `uv` to be installed in the image.

## Usage

These images are built and managed by the `GeminiCliPodmanAnswerGenerator` class in `benchmarks/answer_generators/gemini_cli_podman_answer_generator.py`.
