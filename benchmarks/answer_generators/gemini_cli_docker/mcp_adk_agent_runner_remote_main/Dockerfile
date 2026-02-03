# Inherit from standard base
ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

USER root

# Install uv and git
RUN apt-get update && apt-get install -y curl git && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Clone codebase
RUN mkdir -p /workdir && git clone --branch v1.20.0 https://github.com/google/adk-python.git /workdir

# Set final working directory
WORKDIR /workdir
RUN git init && git add . && touch GEMINI.md

# Setup Gemini CLI with MCP (Remote Mode)
RUN --mount=type=secret,id=github_token \
    git config --global url."https://oauth2:$(cat /run/secrets/github_token)@github.com".insteadOf https://github.com && \
    mkdir -p .gemini && \
    uvx --from "git+https://github.com/ivanmkc/agent-generator.git@mcp_server#subdirectory=tools/adk_knowledge_ext" \
    codebase-knowledge-mcp-manage setup \
    --repo-url "https://github.com/google/adk-python.git" \
    --version "v1.20.0" \
    --force
