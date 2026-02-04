FROM python:3.10-slim

WORKDIR /app

# 0. Install System Deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Install Dependencies
COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
ENV MCP_KNOWLEDGE_BASES='[{"id": "google/adk-python@v1.20.0", "repo_url": "https://github.com/google/adk-python.git", "version": "v1.20.0", "index_url": "file:///tmp/local_index.yaml"}]'

COPY tools/adk_knowledge_ext /tmp/pkg

# Install (will try to download index if we don't block it, or we let it download and then delete)
RUN pip install /tmp/pkg

# Delete the index to simulate missing file scenario
RUN rm -f /usr/local/lib/python3.10/site-packages/adk_knowledge_ext/data/indices/*.yaml
RUN rm -f /usr/local/lib/python3.10/site-packages/adk_knowledge_ext/data/manifest.json

# Copy verification script
COPY tools/adk_knowledge_ext/tests/integration/resilience_missing_index/verify_missing_index.py /app/verify.py

CMD ["python", "/app/verify.py"]
