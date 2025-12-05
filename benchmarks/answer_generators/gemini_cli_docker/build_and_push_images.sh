#!/bin/bash
# Script to build and push Gemini CLI Docker Sandbox images to GCR.
#
# Usage:
#   ./build_and_push_images.sh
#
# Prerequisites:
#   - gcloud CLI must be installed and authenticated.
#   - A default Google Cloud project must be configured with `gcloud config set project <PROJECT_ID>`.

set -e

# Auto-detect PROJECT_ID using gcloud
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
  echo "Error: Google Cloud Project ID could not be detected.\n"
  echo "Please ensure:"
  echo "1. gcloud CLI is installed and authenticated."
  echo "2. A default project is configured: `gcloud config set project <YOUR_PROJECT_ID>`\n"
  exit 1
fi

echo "=========================================================="
echo "Building and Pushing Docker Images for Project: $PROJECT_ID"
echo "=========================================================="

SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR"

# ------------------------------------------------------------------
# 1. Build Base Image (Priority)
# ------------------------------------------------------------------
# The base image is a dependency for others, so it must be built first.
# We explicitly handle it here to set up the necessary local tags.
if [ -d "base" ]; then
  echo ""
  echo "[Base] Building 'base' image..."
  
  # Build and tag for GCR
  docker build -t gcr.io/"$PROJECT_ID"/gemini-cli-base:latest base/
  
  # Add local tags required by other Dockerfiles (dependency satisfaction)
  # Some Dockerfiles might say "FROM gemini-cli-base"
  docker tag gcr.io/"$PROJECT_ID"/gemini-cli-base:latest gemini-cli-base:latest
  # Some might say "FROM adk-gemini-sandbox:base" (legacy)
  docker tag gcr.io/"$PROJECT_ID"/gemini-cli-base:latest adk-gemini-sandbox:base
  
  echo "Pushing gemini-cli-base..."
  docker push gcr.io/"$PROJECT_ID"/gemini-cli-base:latest
else
  echo "Error: 'base' directory not found! Cannot proceed."
  exit 1
fi

# ------------------------------------------------------------------
# 2. Auto-detect and Build Other Images
# ------------------------------------------------------------------
echo ""
echo "[Auto-Detect] Scanning for other Dockerfiles..."

# Iterate over all subdirectories
for dir in */; do
  dirname=${dir%/} # Remove trailing slash
  
  # Skip 'base' as we already handled it
  if [ "$dirname" == "base" ]; then
    continue
  fi

  # Check if directory contains a Dockerfile
  if [ -f "$dirname/Dockerfile" ]; then
    echo "----------------------------------------------------------"
    echo "Found Dockerfile in '$dirname'"
    
    # Determine Image Name
    # Default to directory name
    IMAGE_NAME="$dirname"
    
    # Handle legacy override for adk-python
    if [ "$dirname" == "adk-python" ]; then
      IMAGE_NAME="adk-gemini-sandbox"
      echo "  -> Mapping '$dirname' to image name '$IMAGE_NAME' (Legacy Override)"
    else
      echo "  -> Using directory name as image name: '$IMAGE_NAME'"
    fi
    
    FULL_TAG="gcr.io/$PROJECT_ID/$IMAGE_NAME:latest"
    
    echo "Building $FULL_TAG..."
    docker build -t "$FULL_TAG" "$dirname/"
    
    echo "Pushing $FULL_TAG..."
    docker push "$FULL_TAG"
    
    echo "Done with $dirname."
  fi
done

echo ""
echo "=========================================================="
echo "All discovered images built and pushed successfully!"
echo "=========================================================="
