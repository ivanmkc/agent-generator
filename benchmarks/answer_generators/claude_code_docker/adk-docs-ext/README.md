# ADK Docs Extension (Dockerized)

This directory defines the Docker build context for the `adk-docs-ext` environment. It configures an image based on the Gemini CLI, installing and optimizing the `adk-docs-ext` extension for benchmark execution.

## Contents

*   **`Dockerfile`**: Defines the build steps:
    *   Installs the `adk-docs-ext` extension from the specified git repository.
    *   Installs `uv` and `mcpdoc` locally to ensure low-latency startup (bypassing `uvx`).
    *   Invokes `patch_config.py` to finalize configuration.
*   **`patch_config.py`**: A helper script executed during the build to:
    *   Modify `gemini-extension.json` to use the locally installed `mcpdoc` binary.
    *   Strip `uvx` preambles from command arguments.
    *   Resolve relative paths in `--urls` arguments to absolute paths within the container.

## Build Configuration

The `Dockerfile` accepts the following arguments:

*   `BASE_IMAGE`: (Required) The base image containing the Gemini CLI environment.
*   `EXTENSION_REPO`: The repository URL for the extension (default: `https://github.com/derailed-dash/adk-docs-ext`).
*   `EXTENSION_REF`: The git reference (branch or tag) to install (default: `main`).