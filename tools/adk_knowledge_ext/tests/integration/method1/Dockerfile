FROM python:3.10-slim

WORKDIR /app

# 0. Install System Deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Install Dependencies
# Setup local index for build hook
COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
ENV ADK_INDEX_URL=file:///tmp/local_index.yaml

COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 2. Method 1: Manual Settings Setup
RUN mkdir -p /root/.gemini
COPY tools/adk_knowledge_ext/tests/integration/method1/settings.json /root/.gemini/settings.json

# 3. Verification
COPY tools/adk_knowledge_ext/tests/integration/common/verify_mcp_config.py /app/verify.py

CMD ["python", "/app/verify.py"]
