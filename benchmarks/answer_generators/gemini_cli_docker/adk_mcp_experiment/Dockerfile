# Inherit from standard base
ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

USER root

# Install git for uv to handle git dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the package globally in the container's environment
# We use the token for authentication as the repo may be private
ARG COMMIT_HASH=main
RUN --mount=type=secret,id=github_token \
    export GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" /run/secrets/github_token | cut -d= -f2- | tr -d '"' | tr -d "'") && \
    git config --global url."https://oauth2:${GITHUB_TOKEN}@github.com".insteadOf https://github.com && \
    uv pip install --system "google-adk[mcp-server] @ git+https://github.com/eliasecchig/adk-mcp-experiment.git@${COMMIT_HASH}" && \
    git config --global --unset url."https://oauth2:${GITHUB_TOKEN}@github.com".insteadOf

# Run setup (pipe yes for interactivity)
# This registers the MCP server provided by the installed package
RUN yes | adk mcp setup
