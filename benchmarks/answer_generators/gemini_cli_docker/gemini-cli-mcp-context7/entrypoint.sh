#!/bin/bash
set -e

echo "[Entrypoint] Starting configuration..."

# Check for GEMINI_API_KEY or Vertex AI credentials
if [ -z "$GEMINI_API_KEY" ] && [ -z "$GOOGLE_GENAI_USE_VERTEXAI" ]; then
  echo "[Entrypoint] Error: GEMINI_API_KEY or GOOGLE_GENAI_USE_VERTEXAI environment variable not set."
  exit 1
fi

if [ -z "$CONTEXT7_API_KEY" ]; then
    echo "[Entrypoint] Warning: CONTEXT7_API_KEY is not set. MCP functionality may be limited."
fi

# Substitute environment variables in settings.json
# We only want to substitute CONTEXT7_API_KEY, strictly speaking, but standard envsubst does all.
# If other $vars exist in json, they might be clobbered.
# Using a specific list of variables is safer if needed, but for now we assume settings.json is simple.
echo "[Entrypoint] Substituting variables in settings.json..."
envsubst < /root/.gemini/settings.json.template > /root/.gemini/settings.json

echo "[Entrypoint] Configuration complete. Executing: $@"
exec "$@"
