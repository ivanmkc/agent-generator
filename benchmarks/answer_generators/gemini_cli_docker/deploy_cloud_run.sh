#!/bin/bash
# Script to deploy the ADK Gemini Sandbox to Cloud Run.
#
# Usage:
#   ./deploy_cloud_run.sh [SERVICE_NAME]
#
# Prerequisites:
#   - gcloud CLI installed and authenticated.
#   - Docker images built and pushed (use build_and_push_images.sh first).

set -e

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
  echo "Error: Could not detect Google Cloud Project ID."
  exit 1
fi

SERVICE_NAME=${1:-"adk-gemini-sandbox"}
IMAGE="gcr.io/$PROJECT_ID/adk-gemini-sandbox:latest"
REGION="us-central1"

echo "==========================================================" 
 echo "Deploying to Cloud Run"
 echo "Project: $PROJECT_ID"
 echo "Service: $SERVICE_NAME"
 echo "Image:   $IMAGE"
 echo "=========================================================="

# Deploy as an authenticated service
# We override the command to run the cli_server.py wrapper
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --command "python3" \
  --args "/usr/local/bin/cli_server.py" \
  --no-allow-unauthenticated \
  --project "$PROJECT_ID"

echo ""
 echo "Deployment successful!"
 echo "Service URL: $(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')"
