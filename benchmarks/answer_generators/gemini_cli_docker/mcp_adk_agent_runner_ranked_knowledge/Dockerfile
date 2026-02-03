ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

# Install Python MCP SDK and YAML parser
RUN pip install --no-cache-dir mcp pyyaml rank-bm25

# Clone and Install adk-python
RUN mkdir -p /workdir && git clone --branch v1.20.0 https://github.com/google/adk-python.git /workdir
RUN pip install --no-cache-dir /workdir pytest

# Install extension (now includes bundled index)
COPY tools/adk_knowledge_ext /app/extensions/adk-knowledge-ext
RUN pip install --no-cache-dir /app/extensions/adk-knowledge-ext

# Install ADK Agent Runner tools
COPY benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner_basic/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner_basic/src/ /app/agent-runner/

# Set final working directory to the codebase
WORKDIR /workdir
RUN git init && git add . && touch GEMINI.md

# Setup Gemini CLI with MCP
# Running 'setup' without --knowledge-index-url will default to checking the bundled manifest.
RUN mkdir -p .gemini && \
    codebase-knowledge-mcp-manage setup \
    --repo-url "https://github.com/google/adk-python.git" \
    --version "v1.20.0" \
    --local \
    --force

# Manually add the adk-agent-runner to settings.json
COPY benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner_ranked_knowledge/patch_settings.py /tmp/patch_settings.py
RUN python3 /tmp/patch_settings.py

# Override search provider to vector
ENV ADK_SEARCH_PROVIDER=vector

ENV ADK_SEARCH_PROVIDER=bm25

# Set working directory to repo root so relative paths work if needed
WORKDIR /workdir
