ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

# Install Python MCP SDK and YAML parser
RUN pip install --no-cache-dir mcp pyyaml rank-bm25

# Clone and Install adk-python
RUN mkdir -p /app && git clone --branch v1.20.0 https://github.com/google/adk-python.git /app/adk-python
RUN pip install --no-cache-dir /app/adk-python

# Install uv (Required for the generated configuration)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install extension from Remote GitHub (Main Branch)
RUN pip install "git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext"

# Setup Gemini CLI with MCP (Remote Mode)
# This generates a config using 'uvx --from git+...'
RUN mkdir -p /root/.gemini && \
    mkdir -p /root/.mcp_cache/instructions && \
    codebase-knowledge-mcp-manage setup \
    --repo-url "https://github.com/google/adk-python.git" \
    --version "v1.20.0" \
    --force

ENV ADK_SEARCH_PROVIDER=bm25

# Set working directory to repo root so relative paths work if needed
WORKDIR /workdir
