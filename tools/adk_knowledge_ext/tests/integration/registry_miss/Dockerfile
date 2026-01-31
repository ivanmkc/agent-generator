FROM python:3.10-slim

WORKDIR /app

# 0. Install System Deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Install Dependencies
COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 2. Verification Script
COPY tools/adk_knowledge_ext/tests/integration/registry_miss/verify_miss.py /app/verify.py

CMD ["python", "/app/verify.py"]
