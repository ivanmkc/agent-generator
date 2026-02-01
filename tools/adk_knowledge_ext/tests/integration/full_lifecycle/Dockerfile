FROM gemini-cli:base

# Install dependencies
RUN apt-get update && apt-get install -y curl git && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install mcp (needed for the python verification script acting as client)
RUN pip install mcp

WORKDIR /app

# 1. Copy Source (simulate local checkout)
COPY tools/adk_knowledge_ext /src/tools/adk_knowledge_ext
COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /src/benchmarks/generator/benchmark_generator/data/ranked_targets.yaml

# 2. Patch Registry to point to local file (Build-time dependency)
# This ensures hatch_build.py finds the index and bundles it.
RUN echo "https://github.com/google/adk-python.git:\n  v1.20.0: file:///src/benchmarks/generator/benchmark_generator/data/ranked_targets.yaml\n  main: file:///src/benchmarks/generator/benchmark_generator/data/ranked_targets.yaml" > /src/tools/adk_knowledge_ext/src/adk_knowledge_ext/registry.yaml

# 3. Verification Script
COPY tools/adk_knowledge_ext/tests/integration/full_lifecycle/verify_lifecycle.py /app/verify.py

CMD ["python", "/app/verify.py"]
