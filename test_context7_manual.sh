#!/bin/bash
IMAGE="gemini-cli:mcp-context7"
CONTAINER="debug-context7"
PORT=8082

echo "Starting container..."
# Don't use --rm so we can inspect logs if it dies
podman run -d --name $CONTAINER -p $PORT:8080 -e GEMINI_API_KEY=test -e CONTEXT7_API_KEY=test $IMAGE

echo "Waiting for startup..."
sleep 2

echo "Checking status..."
podman ps -a --filter name=$CONTAINER

echo "Checking logs..."
podman logs $CONTAINER

echo "Stopping/Removing container..."
podman rm -f $CONTAINER
