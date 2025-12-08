#!/bin/bash
set -e

# Default to podman if available, otherwise docker
if command -v podman &> /dev/null; then
    CONTAINER_TOOL="podman"
elif command -v docker &> /dev/null; then
    CONTAINER_TOOL="docker"
else
    echo "Error: Neither podman nor docker found."
    exit 1
fi

# Allow overriding via arg: ./build_local_images.sh [docker|podman]
if [ ! -z "$1" ]; then
    CONTAINER_TOOL=$1
fi

echo "Using container tool: $CONTAINER_TOOL"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. Build Base Image
echo "Building Base Image..."
$CONTAINER_TOOL build \
    -t adk-gemini-sandbox:base \
    -f base/Dockerfile \
    base/

# 2. Build ADK Python Sandbox
echo "Building ADK Python Sandbox..."
$CONTAINER_TOOL build \
    --build-arg BASE_IMAGE=adk-gemini-sandbox:base \
    -t adk-gemini-sandbox:adk-python \
    -f adk-python/Dockerfile \
    adk-python/

# 3. Build MCP Context7 Sandbox
echo "Building MCP Context7 Sandbox..."
$CONTAINER_TOOL build \
    --build-arg BASE_IMAGE=adk-gemini-sandbox:base \
    -t adk-gemini-sandbox:mcp-context7 \
    -f gemini-cli-mcp-context7/Dockerfile \
    gemini-cli-mcp-context7/

# 4. Build ADK Docs Extension Sandbox
echo "Building ADK Docs Extension Sandbox..."
$CONTAINER_TOOL build \
    --build-arg BASE_IMAGE=adk-gemini-sandbox:base \
    -t adk-gemini-sandbox:adk-docs-ext \
    -f adk-docs-ext/Dockerfile \
    adk-docs-ext/

echo "All images built successfully!"
$CONTAINER_TOOL images | grep adk-gemini-sandbox
