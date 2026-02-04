# Inherit from standard base
ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

USER root

# Install uv and git
RUN apt-get update && apt-get install -y curl git && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Clone codebase (to have the context)
RUN mkdir -p /workdir && git clone --branch v1.20.0 https://github.com/google/adk-python.git /workdir

# Set final working directory
WORKDIR /workdir

# Install extension from local copy (for mounting via uvx)
COPY tools/adk_knowledge_ext /app/extensions/adk-knowledge-ext

# Setup Gemini CLI with MCP (Local Mode via uvx)
WORKDIR /workdir
RUN mkdir -p .gemini && \
    uvx --from /app/extensions/adk-knowledge-ext \
    codebase-knowledge-mcp-manage setup \
    --repo-url "https://github.com/google/adk-python.git" \
    --version "v1.20.0" \
    --local "/app/extensions/adk-knowledge-ext" \
    --force

WORKDIR /workdir
