ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

# Install Python MCP SDK and YAML parser
RUN pip install --no-cache-dir mcp pyyaml rank-bm25

# Clone and Install adk-python
RUN mkdir -p /app && git clone --branch v1.20.0 https://github.com/google/adk-python.git /app/adk-python
RUN pip install --no-cache-dir /app/adk-python

# Install extension (now includes bundled index)
COPY tools/adk_knowledge_ext /app/extensions/adk-knowledge-ext
RUN pip install --no-cache-dir /app/extensions/adk-knowledge-ext

# Setup Gemini CLI with MCP
# Running 'setup' without --knowledge-index-url will default to checking the bundled manifest
RUN mkdir -p /root/.gemini && \
    mkdir -p /root/.mcp_cache/instructions && \
    cd /app/extensions/adk-knowledge-ext && \
    codebase-knowledge-mcp-manage setup \
    --repo-url "https://github.com/google/adk-python.git" \
    --version "v1.20.0" \
    --local \
    --force

ENV ADK_SEARCH_PROVIDER=bm25

# Set working directory to repo root so relative paths work if needed
WORKDIR /workdir
