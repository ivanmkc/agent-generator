#!/bin/bash
set -e

PROJECT_ID=$1
REGION=$2
BUCKET_NAME=$3

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ] || [ -z "$BUCKET_NAME" ]; then
    echo "Usage: ./tools/deploy_viewer.sh <PROJECT_ID> <REGION> <BUCKET_NAME>"
    exit 1
fi

IMAGE_NAME="gcr.io/$PROJECT_ID/adk-benchmark-viewer"

echo "Building Docker image..."
docker build -t $IMAGE_NAME -f tools/viewer/Dockerfile.viewer .

echo "Pushing Docker image..."
docker push $IMAGE_NAME

echo "Deploying to Cloud Run..."
gcloud run deploy adk-benchmark-viewer \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars BENCHMARK_GCS_BUCKET=$BUCKET_NAME \
    --project $PROJECT_ID
