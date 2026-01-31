FROM python:3.10-slim

WORKDIR /app

# 1. Install Dependencies
# Copy the whole package context to install it
COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 2. Setup Data
RUN mkdir -p /data/adk-python
COPY tools/adk_knowledge_ext/tests/integration/common/dummy_ranked_targets.yaml /data/ranked_targets.yaml

# 3. Method 1: Manual Settings Setup
RUN mkdir -p /root/.gemini
COPY tools/adk_knowledge_ext/tests/integration/method1/settings.json /root/.gemini/settings.json

# 4. Verification
COPY tools/adk_knowledge_ext/tests/integration/common/verify_mcp_config.py /app/verify.py

CMD ["python", "/app/verify.py"]
