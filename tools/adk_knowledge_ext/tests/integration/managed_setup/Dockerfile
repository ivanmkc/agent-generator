FROM python:3.10-slim

WORKDIR /app

# 0. Install System Deps
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Install Dependencies
COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 2. Setup Mock Gemini CLI
COPY tools/adk_knowledge_ext/tests/integration/managed_setup/mock_gemini.sh /usr/local/bin/gemini
RUN chmod +x /usr/local/lib/python3.10/site-packages/adk_knowledge_ext/manage_mcp.py
RUN chmod +x /usr/local/bin/gemini

# 3. Verification Script
COPY tools/adk_knowledge_ext/tests/integration/managed_setup/verify_managed_setup.py /app/verify.py

CMD ["python", "/app/verify.py"]
