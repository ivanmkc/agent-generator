FROM python:3.10-slim

WORKDIR /app

# 0. Install System Deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 2. Install Test Dependencies
RUN pip install mcp

# 3. Setup Local Data
COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
COPY tools/adk_knowledge_ext /tmp/pkg

# 4. Method 2: Extension Installation Simulator
COPY tools/adk_knowledge_ext/tests/integration/extension_uvx/install_extension.py /app/install.py
RUN python /app/install.py

# 3. Verification Script
COPY tools/adk_knowledge_ext/tests/integration/common/verify_mcp_config.py /app/verify.py

CMD ["python", "/app/verify.py"]