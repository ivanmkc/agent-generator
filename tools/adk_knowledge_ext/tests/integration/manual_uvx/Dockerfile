FROM python:3.10-slim

WORKDIR /app

# 0. Install System Deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 2. Install Test Dependencies (mcp client library)
RUN pip install mcp

# 3. Setup Local Data
COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
COPY tools/adk_knowledge_ext /tmp/pkg

# 4. Method 1 Config
RUN mkdir -p /root/.gemini
COPY tools/adk_knowledge_ext/tests/integration/method1/settings.json /root/.gemini/settings.json
RUN python3 -c "import json; f='/root/.gemini/settings.json'; d=json.load(open(f)); d['mcpServers']['test-codebase']['env']['TARGET_INDEX_URL']='file:///tmp/local_index.yaml'; json.dump(d, open(f,'w'))"

# 5. Verification
COPY tools/adk_knowledge_ext/tests/integration/common/verify_mcp_config.py /app/verify.py

CMD ["python", "/app/verify.py"]