FROM python:3.10-slim

WORKDIR /app

# 0. Install System Deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 2. Install Dependencies
COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 2. Make script executable
RUN chmod +x /usr/local/lib/python3.10/site-packages/adk_knowledge_ext/manage_mcp.py

# 3. Verification Script
COPY tools/adk_knowledge_ext/tests/integration/managed_json_setup/verify_json.py /app/verify.py

CMD ["python", "/app/verify.py"]
