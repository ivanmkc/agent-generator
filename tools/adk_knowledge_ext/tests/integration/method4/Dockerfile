FROM python:3.10-slim

WORKDIR /app

# 0. Install System Deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Install Dependencies (Bundles index)
COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
ENV ADK_INDEX_URL=file:///tmp/local_index.yaml

COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 2. SABOTAGE: Delete the bundled index
# We need to find where it was installed.
# Usually /usr/local/lib/python3.10/site-packages/adk_knowledge_ext/data/indices/ranked_targets_v1.20.0.yaml
RUN rm /usr/local/lib/python3.10/site-packages/adk_knowledge_ext/data/indices/ranked_targets_v1.20.0.yaml

# 3. Verification Script
COPY tools/adk_knowledge_ext/tests/integration/method4/verify_missing_index.py /app/verify.py

CMD ["python", "/app/verify.py"]
