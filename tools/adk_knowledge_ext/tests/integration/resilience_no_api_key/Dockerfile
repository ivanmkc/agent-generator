FROM python:3.10-slim

WORKDIR /app

# 0. Install System Deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Install Dependencies
COPY tools/adk_knowledge_ext/src/adk_knowledge_ext/data/indices/google-adk-python/v1.24.1/ranked_targets.yaml /tmp/local_index.yaml
ENV MCP_KNOWLEDGE_BASES='[{"id": "google/adk-python@v1.20.0", "repo_url": "https://github.com/google/adk-python.git", "version": "v1.20.0", "index_url": "file:///tmp/local_index.yaml"}]'
ENV ADK_SEARCH_PROVIDER=hybrid

COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 2. Verification Script
COPY tools/adk_knowledge_ext/tests/integration/resilience_no_api_key/verify_fail_no_key.py /app/verify.py

CMD ["python", "/app/verify.py"]
