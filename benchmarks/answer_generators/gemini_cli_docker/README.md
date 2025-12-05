# Gemini CLI Docker Sandbox

This directory provides the infrastructure for running benchmarks in a sandboxed Docker environment using the Gemini CLI. It utilizes a **multi-stage build approach** where a common "base" image supports multiple "variant" images with different tool or agent configurations.

## Directory Structure

*   `base/`: The foundation image.
    *   **Dockerfile:** Installs Python 3.11, Node.js 22.x, git, curl, `uv`, and `@google/gemini-cli`.
    *   **Tag:** `gemini-cli-base`

*   `adk-python/`: The standard variant for the Python ADK.
    *   **Dockerfile:** Inherits from `gemini-cli-base`. Clones the `adk-python` repo into `/repos/adk-python`.
    *   **Tag:** `adk-gemini-sandbox:adk-python` (or `:latest`)
    *   **Purpose:** Standard environment for testing agents against the codebase.

*   `gemini-cli-mcp-context7/`: A variant configured with an MCP server.
    *   **Dockerfile:** Inherits from `gemini-cli-base`. Installs `mcp` Python package and configures `settings.json`.
    *   **Tag:** `gemini-cli-mcp-context7`
    *   **Purpose:** Tests the Gemini CLI's ability to use the `context7` MCP server (remote HTTP) to access repository context.

## Usage

### Build and Push Images

We provide a helper script to automatically build all Docker images (base and variants) and push them to your Google Container Registry (GCR).

**Usage:**
```bash
cd benchmarks/answer_generators/gemini_cli_docker/
./build_and_push_images.sh <YOUR_PROJECT_ID>
```

This script will:
1.  Build the `base` image first.
2.  Auto-detect and build all other variant images in subdirectories.
3.  Tag them appropriately (e.g., `gcr.io/<PROJECT_ID>/adk-gemini-sandbox:latest`).
4.  Push all images to GCR.

### Cloud Run Deployment

To run benchmarks against a Cloud Run hosted environment (instead of local Docker), you can deploy the sandbox as a service.

#### Prerequisites

To deploy a `GeminiCliCloudRunAnswerGenerator`, ensure the following Google Cloud prerequisites are met:

```bash
export YOUR_GCP_PROJECT_ID=<YOUR_GCP_PROJECT_ID> # Replace with your GCP Project ID
export YOUR_GCP_EMAIL_ADDRESS=<YOUR_GCP_EMAIL_ADDRESS> # Replace with your GCP email
export PROJECT_NUMBER=$(gcloud projects describe $YOUR_GCP_PROJECT_ID --format='value(projectNumber)')
export CLOUD_BUILD_SERVICE_ACCOUNT="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"
export COMPUTE_ENGINE_SERVICE_ACCOUNT="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
```

1.  **Enable Cloud Build API**: This API is required for building Docker images from your source code.
    *   Visit: [https://console.cloud.google.com/apis/api/cloudbuild.googleapis.com/overview](https://console.cloud.google.com/apis/api/cloudbuild.googleapis.com/overview)
    *   Select your project and click "Enable".

2.  **Grant Cloud Run Invoker Role (to your user)**: Your Google Cloud user account needs permission to invoke the deployed Cloud Run service for testing and interaction.
    *   Run in your terminal (replace `YOUR_GCP_REGION`):
        ```bash
        export YOUR_GCP_REGION=<YOUR_GCP_REGION>
        gcloud run services add-iam-policy-binding adk-gemini-sandbox \
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

#### Deployment Script

**Deploy:**
```bash
cd benchmarks/answer_generators/gemini_cli_docker/
./deploy_cloud_run.sh <SERVICE_NAME>
# Defaults to 'adk-gemini-sandbox' if SERVICE_NAME is omitted.
```
This script deploys the `adk-gemini-sandbox` image (built in the previous step) and outputs the Service URL.

### Running Benchmarks

You can run benchmarks using either the local Docker integration or the Cloud Run integration.

**Local Docker:**
```python
from benchmarks.answer_generators.gemini_cli_docker import GeminiCliDockerAnswerGenerator

PROJECT_ID = "your-project-id"

generator_local = GeminiCliDockerAnswerGenerator(
    model_name="gemini-2.5-flash",
    image_name=f"gcr.io/{PROJECT_ID}/adk-gemini-sandbox:latest"
)
```

**Cloud Run:**
```python
from benchmarks.answer_generators.gemini_cli_docker import GeminiCliCloudRunAnswerGenerator

SERVICE_URL = "https://adk-gemini-sandbox-xyz.a.run.app" # Output from deploy script

generator_cloud = GeminiCliCloudRunAnswerGenerator(
    model_name="gemini-2.5-flash",
    service_url=SERVICE_URL,
    auto_deploy=True  # Optional: Auto-deploys if service is unreachable
)
```
