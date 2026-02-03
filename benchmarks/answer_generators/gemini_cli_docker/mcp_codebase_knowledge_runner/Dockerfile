# Inherit from standard base
ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

USER root

# Clone and Install adk-python
RUN mkdir -p /workdir && git clone --branch v1.20.0 https://github.com/google/adk-python.git /workdir
RUN pip install --no-cache-dir /workdir pytest

# Install extension (now includes bundled index)
COPY tools/adk_knowledge_ext /app/extensions/adk-knowledge-ext
RUN pip install --no-cache-dir /app/extensions/adk-knowledge-ext

# Set final working directory to the codebase
WORKDIR /workdir
RUN git init && git add . && touch GEMINI.md

# Setup Gemini CLI with MCP
RUN mkdir -p .gemini && \
    codebase-knowledge-mcp-manage setup \
    --repo-url "https://github.com/google/adk-python.git" \
    --version "v1.20.0" \
    --local \
    --force

# Override search provider to hybrid for generic runner
ENV ADK_SEARCH_PROVIDER=hybrid
