FROM python:3.10-slim

WORKDIR /app

# 0. Install System Deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Setup Local Index for Testing
COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml

# 2. Install Dependencies
COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 3. OVERRIDE Registry for Test (Point to local file)
# We overwrite the installed registry.yaml to ensure we test the LOOKUP logic
# without relying on external internet URLs.
RUN echo "https://github.com/google/adk-python.git:\n  v1.20.0: file:///tmp/local_index.yaml" > /usr/local/lib/python3.10/site-packages/adk_knowledge_ext/registry.yaml

# 4. Verification Script
COPY tools/adk_knowledge_ext/tests/integration/registry_lookup/verify_registry.py /app/verify.py

CMD ["python", "/app/verify.py"]