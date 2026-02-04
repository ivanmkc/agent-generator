# Inherit from standard base
ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

USER root

# Install uv and git
RUN apt-get update && apt-get install -y curl git && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Setup Gemini CLI with MCP (Remote Mode)
WORKDIR /workdir
COPY tools/adk_knowledge_ext /app/extensions/adk-knowledge-ext
RUN --mount=type=secret,id=github_token \
    # 1. Extract GITHUB_TOKEN from the mounted .env secret
    #    - grep: find the line starting with GITHUB_TOKEN=
    #    - cut: get everything after the '=' (fields 2 and beyond)
    #    - tr: strip any surrounding single or double quotes
    export GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" /run/secrets/github_token | cut -d= -f2- | tr -d '"' | tr -d "'") && \
    # 2. Configure git to use the token for authentication against github.com
    git config --global url."https://oauth2:${GITHUB_TOKEN}@github.com".insteadOf https://github.com && \
    uvx --from /app/extensions/adk-knowledge-ext \
    codebase-knowledge-mcp-manage setup \
    --kb-ids "adk-python-v1.20.0" \
    --quiet && \
    # 3. Clean up credentials to avoid leaking token in image layer
    git config --global --unset url."https://oauth2:${GITHUB_TOKEN}@github.com".insteadOf
