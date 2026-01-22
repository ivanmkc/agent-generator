# CI/CD & Deployment Plan for Benchmarks

## 1. Automated Validation (CI)
**Objective:** Ensure code integrity on every Pull Request.

**File:** `.github/workflows/benchmark_ci.yml`
**Triggers:** Push/PR to `main` (paths: `benchmarks/**`, `tools/**`).

**Steps:**
1.  **Setup:** Checkout, Python 3.12, Install dependencies.
2.  **Test:** Run `pytest benchmarks/tests/integration/test_ground_truth_answer_generator.py` (Validation only).
    *   *Note:* Does not require `GEMINI_API_KEY` or GCS.

## 2. Full Benchmark Execution (Manual/Scheduled)
**Objective:** Run the expensive LLM benchmarks and archive results to GCS for viewing.

**File:** `.github/workflows/benchmark_run.yml`
**Triggers:** `workflow_dispatch` (Manual) or Schedule (e.g., Weekly).

**Secrets Required:**
*   `GEMINI_API_KEY`: For the LLM generation.
*   `GCP_CREDENTIALS` (Service Account JSON): For GCS upload.

**Environment Variables:**
*   `BENCHMARK_GCS_BUCKET`: The name of the GCS bucket (e.g., `my-benchmark-results`).

**Steps:**
1.  **Setup:** Checkout, Python 3.12, Install dependencies.
2.  **Auth:** `google-github-actions/auth` using `GCP_CREDENTIALS`.
3.  **Run & Upload:**
    *   Execute: `notebooks/run_benchmarks.sh --model-filter gemini-2.5-flash`
    *   The script internally checks `BENCHMARK_GCS_BUCKET` and uploads artifacts (`results.json`, `trace.yaml`, etc.) to `gs://$BUCKET_NAME/$TIMESTAMP/`.

## 3. Hosted Viewer Deployment (Cloud Run)
**Objective:** Host the Streamlit Viewer to visualize results from the GCS bucket.

**Prerequisites:**
1.  **GCS Bucket:** Create a bucket (e.g., `gs://adk-benchmark-results`).
2.  **Service Account:** The Cloud Run service account must have `Storage Object Viewer` permission on the bucket.

**Deployment Script:** `tools/deploy_viewer.sh`

**Usage:**
```bash
# Run from project root
./tools/deploy_viewer.sh <PROJECT_ID> <REGION> <BUCKET_NAME>
```

**What it does:**
1.  Builds the Docker image using `tools/Dockerfile.viewer`.
2.  Deploys to Cloud Run.
3.  Sets the `BENCHMARK_GCS_BUCKET` environment variable on the container.

**Viewer Logic:**
*   The Viewer (`tools/benchmark_viewer.py`) checks `BENCHMARK_GCS_BUCKET`.
*   It lists available runs from the bucket.
*   On selection, it downloads the run artifacts to a local cache within the container instance.

## Summary of Changes Made
1.  **Requirements:** Added `google-cloud-storage` to `requirements.txt`.
2.  **Viewer:** Updated `tools/benchmark_viewer.py` to transparently list and fetch runs from GCS.
3.  **Runner:** Updated `notebooks/run_benchmarks.sh` to upload results to GCS if the bucket env var is set.
4.  **Deployment:** Created `tools/Dockerfile.viewer` and `tools/deploy_viewer.sh`.
