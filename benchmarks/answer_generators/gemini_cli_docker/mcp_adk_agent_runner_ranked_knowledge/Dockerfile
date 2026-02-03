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

# Install ADK Agent Runner tools
COPY benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner_basic/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner_basic/src/ /app/agent-runner/

# Set final working directory
WORKDIR /workdir

# Install extension from local copy (for mounting via uvx)
COPY tools/adk_knowledge_ext /app/extensions/adk-knowledge-ext

# Setup Gemini CLI with MCP (Local Mode via uvx)
RUN uvx --from /app/extensions/adk-knowledge-ext \
    codebase-knowledge-mcp-manage setup \
    --repo-url "https://github.com/google/adk-python.git" \
    --version "v1.20.0" \
    --local \
    --force

# Manually add the adk-agent-runner to settings.json
COPY benchmarks/answer_generators/gemini_cli_docker/mcp_adk_agent_runner_ranked_knowledge/patch_settings.py /tmp/patch_settings.py
RUN python3 /tmp/patch_settings.py
