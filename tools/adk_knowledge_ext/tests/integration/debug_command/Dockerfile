FROM python:3.10-slim

WORKDIR /app

# Install deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Setup Fake Registry/Index
COPY tools/adk_knowledge_ext/src/adk_knowledge_ext/data/indices/google-adk-python/v1.24.1/ranked_targets.yaml /tmp/local_index.yaml
COPY tools/adk_knowledge_ext /tmp/pkg

# Install
RUN pip install /tmp/pkg

# Inject registry pointing to local index (Bundled mode)
# We overwrite the installed registry.yaml
RUN echo "repositories:\n  test/repo:\n    repo_url: https://test.com/repo.git\n    default_version: v1\n    description: Test Repo\n    versions:\n      v1:\n        index_url: file:///tmp/local_index.yaml" > /usr/local/lib/python3.10/site-packages/adk_knowledge_ext/registry.yaml

# Setup Fake Gemini Config
RUN mkdir -p /root/.gemini
RUN echo '{"mcpServers": {"codebase-knowledge": {"command": "uvx", "args": ["--from", "/tmp/pkg", "codebase-knowledge-mcp"], "env": {"MCP_KNOWLEDGE_BASES": "[]"}}}}' > /root/.gemini/settings.json

# Verify Script
COPY tools/adk_knowledge_ext/tests/integration/debug_command/verify_debug.py /app/verify.py

CMD ["python", "/app/verify.py"]
