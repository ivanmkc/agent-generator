#!/bin/bash

# Substitute environment variables in settings.json
envsubst < /root/.gemini/settings.json.template > /root/.gemini/settings.json

# Check for GEMINI_API_KEY or Vertex AI credentials
if [ -z "$GEMINI_API_KEY" ] && [ -z "$GOOGLE_GENAI_USE_VERTEXAI" ]; then
  echo "Error: GEMINI_API_KEY or GOOGLE_GENAI_USE_VERTEXAI environment variable not set."
  exit 1
fi

# Pass through all arguments
exec "$@"
