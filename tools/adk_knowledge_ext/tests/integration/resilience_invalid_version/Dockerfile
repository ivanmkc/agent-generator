FROM python:3.10-slim

WORKDIR /app

# 0. Install System Deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Install Dependencies
COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
ENV TARGET_VERSION=v1.20.0
ENV TARGET_INDEX_URL=file:///tmp/local_index.yaml

COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 2. Verification Script
COPY tools/adk_knowledge_ext/tests/integration/method3/verify_resilience.py /app/verify.py

CMD ["python", "/app/verify.py"]