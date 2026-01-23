# Gemini CLI Docker Sandbox

This directory provides the infrastructure for running benchmarks in a sandboxed Docker environment using the Gemini CLI. It utilizes a **multi-stage build approach** where a common "base" image supports multiple "variant" images with different tool or agent configurations.

## Architecture & Concurrency

The sandbox server (`base/cli_server.py`) is built using **FastAPI** and **Uvicorn**, utilizing asynchronous subprocess management.

*   **High Concurrency:** The server uses `asyncio` to handle concurrent requests efficiently. A single container instance can handle **100+ concurrent requests** without blocking, limited only by system resources (CPU/RAM) rather than thread limits.
*   **Non-Blocking:** CLI commands are executed as non-blocking subprocesses, allowing the event loop to continue serving other requests while waiting for long-running operations (like LLM generation or shell commands).
*   **Optimization:** This architecture allows for high throughput during parallel benchmark execution.

## Tuning Concurrency

The concurrency settings for the benchmark run must be tuned based on the execution environment.

### 1. Local Podman (VM-Based)

Running benchmarks locally on macOS/Windows uses a Podman VM, which has strict resource and networking limits (specifically the `gvproxy` networking stack).

*   **Global Limit (`MAX_GLOBAL_CONCURRENCY`):** **10** (Recommended safe maximum).
    *   *Reason:* While the VM might have enough RAM, the `gvproxy` networking stack often becomes unstable with higher concurrent connection counts (e.g., >25), leading to "Connection Refused" errors.
*   **Memory Requirement:** The Podman VM **must** be provisioned with at least **8GB RAM** (`podman machine set --memory 8192`).

### How to Recalculate Limits

1.  **Run the Stress Test:**
    Execute the integration test `benchmarks/tests/integration/test_cloud_run_stability.py` locally or against a deployed service.
    ```bash
    env/bin/python -m pytest benchmarks/tests/integration/test_cloud_run_stability.py
    ```

2.  **Analyze Results:**
    *   If you see `503 Service Unavailable` -> Container is crashing (likely OOM). Reduce `MAX_INSTANCE_CONCURRENCY`.
    *   If you see `429 Rate Exceeded` -> Queue is full. Check if Cloud Run is scaling fast enough or if you hit project quotas.

3.  **Update Configuration:**
    Modify `benchmarks/config.py` with your new values.

## Directory Structure

*   `image_definitions.py`: Defines image configurations (e.g., base image dependencies, build arguments) primarily used by local Podman builds. Cloud Build uses `cloudbuild.yaml` for its build definitions.
*   `base/`: The foundation image.
    *   **Dockerfile:** Installs Python 3.11, Node.js 22.x, git, curl, `uv`, `@google/gemini-cli`, **FastAPI**, and **Uvicorn**.
    *   **Server:** `cli_server.py` (FastAPI app).
    *   **Tag:** `gemini-cli:base`

*   `adk-python/`: The standard variant for the Python ADK.
    *   **Dockerfile:** Inherits from `gemini-cli-base`. Clones the `adk-python` repo into `/workdir/repos/adk-python`.
    *   **Tag:** `gemini-cli:adk-python`
    *   **Purpose:** Standard environment for testing agents against the codebase.

*   `gemini-cli-mcp-context7/`: A variant configured with an MCP server.
    *   **Dockerfile:** Inherits from `gemini-cli-base`. Installs `mcp` Python package and configures `settings.json`.
    *   **Tag:** `gemini-cli:mcp-context7`
    *   **Purpose:** Tests the Gemini CLI's ability to use the `context7` MCP server (remote HTTP) to access repository context.

## Local Development (Podman/Docker)

For local testing and development, you can use the `GeminiCliPodmanAnswerGenerator`.

*   **Auto-Build:** The generator automatically detects missing images and builds them from source using `podman build`. You do not need to manually build images before running tests.
*   **Polymorphism:** The class shares the same API signature as the Cloud Run generator, allowing for seamless swapping between local and cloud execution.

```python
from benchmarks.answer_generators.gemini_cli_docker import GeminiCliPodmanAnswerGenerator
from benchmarks.answer_generators.gemini_cli_docker.image_definitions import IMAGE_DEFINITIONS

# Uses local image 'gemini-cli:adk-python'
# Automatically builds if missing
generator = GeminiCliPodmanAnswerGenerator(
    image_name="gemini-cli:adk-python", 
    dockerfile_dir="benchmarks/answer_generators/gemini_cli_docker/adk-python",
    image_definitions=IMAGE_DEFINITIONS,
    model_name="gemini-2.5-flash"
)
```

### Testing Dockerfiles (Launching a Shell)

You can launch an interactive shell within any of the built Docker images to test them or explore their environment. Replace `<image-name>` with the appropriate image tag.

**1. Base Image**
```bash
podman run -it --rm --entrypoint /bin/bash gemini-cli:base
```

**2. ADK Python Image**
```bash
podman run -it --rm --entrypoint /bin/bash gemini-cli:adk-python
```

**3. ADK Docs Extension Image**
```bash
podman run -it --rm --entrypoint /bin/bash gemini-cli:adk-docs-ext
```

**4. MCP Context 7 Image**
```bash
podman run -it --rm --entrypoint /bin/bash gemini-cli:mcp-context7
```

### Troubleshooting

### Podman Base Image Not Found / Docker Hub Pull Attempt

**Problem:** When running local Podman benchmarks, you might encounter errors like `RuntimeError: Failed to build custom image ...: Error: creating build container: unable to copy from source docker://gemini-cli:base: ... requested access to the resource is denied`. This indicates that Podman is attempting to pull the `gemini-cli:base` image from `docker.io` instead of building it locally, or resolving it from your local image store. This often happens because:
1.  The `base` image has not been built yet.
2.  Your Podman environment (especially on macOS where Podman runs in a VM) is misconfigured to prioritize remote registries or fails to correctly resolve local image names.

**Workaround (Manual Build):**
You can manually build the `base` image once to populate your local Podman image store. After this, subsequent builds for dependent images (like `adk-python`) should succeed without attempting a remote pull.

```bash
podman build -t gemini-cli:base -f benchmarks/answer_generators/gemini_cli_docker/base/Dockerfile benchmarks/answer_generators/gemini_cli_docker/base
```

**Permanent Fix (Podman Configuration):**
For a permanent solution, investigate your Podman configuration files *inside your Podman Machine VM* (if on macOS/Windows) or on your Linux host. Specifically, check:

*   **`/etc/containers/registries.conf`** or **`~/.config/containers/registries.conf`**: Ensure that `gemini-cli` is not implicitly being mapped to a remote registry, or explicitly add `localhost/gemini-cli` to your `[registries.insecure]` or `[registries.search]` lists if you intend to manage it locally.
*   **`/etc/containers/policy.json`** or **`~/.config/containers/policy.json`**: Review policies that might restrict local image resolution or impose signing requirements that block un-pushed local images.