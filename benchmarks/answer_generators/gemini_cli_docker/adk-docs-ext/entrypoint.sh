#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Use envsubst to replace environment variables in the settings.json template
envsubst < /root/.gemini/settings.json.template > /root/.gemini/settings.json

# Execute the command passed as arguments
exec "$@"