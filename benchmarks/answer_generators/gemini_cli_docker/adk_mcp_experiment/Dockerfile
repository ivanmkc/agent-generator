# Inherit from standard base
ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

USER root

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app/adk-mcp-experiment

# Use secret for cloning
RUN --mount=type=secret,id=github_token \
    export GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" /run/secrets/github_token | cut -d= -f2- | tr -d '"' | tr -d "'") && \
    git config --global url."https://oauth2:${GITHUB_TOKEN}@github.com".insteadOf https://github.com && \
    git clone https://github.com/eliasecchig/adk-mcp-experiment.git . && \
    git config --global --unset url."https://oauth2:${GITHUB_TOKEN}@github.com".insteadOf

# Sync dependencies with extra
RUN uv sync --extra mcp-server

# Run setup (pipe yes for interactivity)
RUN yes | uv run adk mcp setup --dev
