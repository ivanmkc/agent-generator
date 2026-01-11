#!/bin/bash

# Ensure the Docker container is running and accessible on port 8080.
# Example to run the container (if not already running):
# podman run --rm -p 8080:8080 -e GEMINI_API_KEY=$GEMINI_API_KEY gemini-cli:adk-docs-ext

curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{
    "args": ["gemini", "--output-format", "stream-json", "--yolo", "--debug", "what is the base class for all adk-python agents"],
    "env": {"GEMINI_API_KEY": "AIzaSyD6i8FCnka6y-dQCA3J8mcIzNRQ-lqOSj8"}
  }'

