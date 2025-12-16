# Gemini CLI Docker Sandbox

This directory provides the infrastructure for running benchmarks in a sandboxed Docker environment using the Gemini CLI. It utilizes a **multi-stage build approach** where a common "base" image supports multiple "variant" images with different tool or agent configurations.

## Architecture & Concurrency

The sandbox server (`base/cli_server.py`) is built using **FastAPI** and **Uvicorn**, utilizing asynchronous subprocess management.

*   **High Concurrency:** The server uses `asyncio` to handle concurrent requests efficiently. A single container instance can handle **100+ concurrent requests** without blocking, limited only by system resources (CPU/RAM) rather than thread limits.
*   **Non-Blocking:** CLI commands are executed as non-blocking subprocesses, allowing the event loop to continue serving other requests while waiting for long-running operations (like LLM generation or shell commands).
*   **Optimization:** This architecture allows `GeminiCliCloudRunAnswerGenerator` to achieve high throughput even with `max_instance_count=1`, preventing `429 Rate Exceeded` errors during parallel benchmark execution.

## Tuning Concurrency

The concurrency settings for the benchmark run are derived from stress testing the container image.

### Validated Configuration (Horizontal Scaling)

We utilize a **Horizontal Scaling** strategy to handle high concurrency. Instead of one large instance, we use multiple smaller instances.

*   **Instance Spec:** 4GB RAM / 4 vCPU.
*   **Per-Instance Limit (`MAX_INSTANCE_CONCURRENCY`):** **10**.
    *   *Reason:* Node.js processes (gemini CLI) consume ~100-200MB memory each. 10 concurrent requests fit safely within 4GB RAM. Exceeding this risks OOM crashes (503 errors).
*   **Global Limit (`MAX_BENCHMARK_CONCURRENCY`):** **40**.
    *   *Reason:* This allows running 40 benchmarks in parallel. Cloud Run automatically scales out to ~4-10 instances to handle this load with zero infrastructure errors.

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
    *   **Dockerfile:** Inherits from `gemini-cli-base`. Clones the `adk-python` repo into `/repos/adk-python`.
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

# Uses local image 'gemini-cli:adk-python'
# Automatically builds if missing
generator = GeminiCliPodmanAnswerGenerator(
    image_name="gemini-cli:adk-python", 
    dockerfile_dir="benchmarks/answer_generators/gemini_cli_docker/adk-python",
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

## Cloud Run Deployment

## Cloud Run Deployment

To run benchmarks against a Cloud Run hosted environment (instead of local Docker), you can deploy the sandbox as a service.

#### Prerequisites

To deploy a `GeminiCliCloudRunAnswerGenerator`, ensure the following Google Cloud prerequisites are met:

```bash
export YOUR_GCP_PROJECT_ID=<YOUR_GCP_PROJECT_ID> # Replace with your GCP Project ID
export YOUR_GCP_EMAIL_ADDRESS=<YOUR_GCP_EMAIL_ADDRESS> # Replace with your GCP email
export YOUR_GCP_REGION=<YOUR_GCP_REGION> # Replace with your GCP region
export PROJECT_NUMBER=$(gcloud projects describe $YOUR_GCP_PROJECT_ID --format='value(projectNumber)')
export CLOUD_BUILD_SERVICE_ACCOUNT="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"
export COMPUTE_ENGINE_SERVICE_ACCOUNT="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
```

1.  **Enable Cloud Build API**: This API is required for building Docker images from your source code.
    *   Visit: [https://console.cloud.google.com/apis/api/cloudbuild.googleapis.com/overview](https://console.cloud.google.com/apis/api/cloudbuild.googleapis.com/overview)
    *   Select your project and click "Enable".

2.  **Grant Cloud Run Invoker Role (to your user)**: Your Google Cloud user account needs permission to invoke the deployed Cloud Run service for testing and interaction.
    *   Run in your terminal:
        ```bash        
        gcloud run services add-iam-policy-binding gemini-cli-sandbox \
            --member="user:$YOUR_GCP_EMAIL_ADDRESS" \
            --role="roles/run.invoker" \
            --region="$YOUR_GCP_REGION"
        ```
    *   Default region for benchmarks is `us-central1`.

3.  **Grant Storage Object Viewer Role (to Cloud Build Service Account)**: The Cloud Build service account requires permission to read the source code archives uploaded to your GCS staging bucket. To apply this role at the project level (for all buckets in the project):
    *   Run in your terminal:
        ```bash
        gcloud projects add-iam-policy-binding $YOUR_GCP_PROJECT_ID \
            --member="$CLOUD_BUILD_SERVICE_ACCOUNT" \
            --role="roles/storage.objectViewer"
gcloud projects add-iam-policy-binding $YOUR_GCP_PROJECT_ID \
            --member="$COMPUTE_ENGINE_SERVICE_ACCOUNT" \
            --role="roles/storage.objectViewer"
        ```

4.  **Grant Logs Writer Role (to Cloud Build Service Account)**: The Cloud Build service account requires permission to write build logs to Cloud Logging.
    *   Run in your terminal:
        ```bash
        gcloud projects add-iam-policy-binding $YOUR_GCP_PROJECT_ID \
            --member="$CLOUD_BUILD_SERVICE_ACCOUNT" \
            --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding $YOUR_GCP_PROJECT_ID \
            --member="$COMPUTE_ENGINE_SERVICE_ACCOUNT" \
            --role="roles/logging.logWriter"            
        ```

5.  **Grant Logs Viewer Role (to your user)**: To debug build failures by viewing logs in the Google Cloud Console, your user account needs the Logs Viewer role.
    Run in your terminal:
        ```bash
        gcloud projects add-iam-policy-binding $YOUR_GCP_PROJECT_ID \
            --member="user:$YOUR_GCP_EMAIL_ADDRESS" \
            --role="roles/logging.viewer"
        ```
    **Note**: This command was crucial for resolving the "You don't have permission to view the logs" error during test execution. The initial "Cloud Run deployment failed" error (related to `storage.objects.get` permissions) was addressed by refactoring the GCS upload logic in `benchmarks/answer_generators/cloud_deploy_utils.py` to use the `google-cloud-storage` Python client directly, ensuring proper credentials for Cloud Build access to staged source code.

6.  **Grant Artifact Registry Writer Role (to Cloud Build Service Account)**: The Cloud Build service account needs permission to push built Docker images to Artifact Registry (which backs gcr.io in newer projects).
    *   Run in your terminal:
        ```bash
        gcloud projects add-iam-policy-binding $YOUR_GCP_PROJECT_ID \
            --member="$CLOUD_BUILD_SERVICE_ACCOUNT" \
            --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $YOUR_GCP_PROJECT_ID \
            --member="$COMPUTE_ENGINE_SERVICE_ACCOUNT" \
            --role="roles/artifactregistry.writer"
        ```

7.  **Grant Artifact Registry CreateOnPush Writer Role (to Cloud Build Service Account)**: If the `gcr.io` repository does not exist in Artifact Registry, this role allows Cloud Build to create it automatically when pushing an image for the first time.
    *   Run in your terminal:
        ```bash
        gcloud projects add-iam-policy-binding $YOUR_GCP_PROJECT_ID \
            --member="$CLOUD_BUILD_SERVICE_ACCOUNT" \
            --role="roles/artifactregistry.createOnPushWriter"
        ```

8.  **Setup Application Default Credentials (ADC)**: For local tests to authenticate with the deployed Cloud Run service, you must generate local credentials.
    *   Run in your terminal:
        ```bash
        gcloud auth application-default login
        ```
    *   Follow the browser prompt to log in with your Google Cloud user account.

#### Deployment Usage

**Cloud Run:**
```python
from benchmarks.answer_generators.gemini_cli_docker import GeminiCliCloudRunAnswerGenerator

generator_cloud = GeminiCliCloudRunAnswerGenerator(
    service_name="gemini-cli-sandbox",
    dockerfile_dir="benchmarks/answer_generators/gemini_cli_docker/adk-python",
    model_name="gemini-2.5-flash",
    auto_deploy=True  # Auto-deploys if version mismatch
)
```