FROM python:3.10-slim

WORKDIR /app

# 1. Install Dependencies
COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 2. Setup Data (Matches default gemini-extension.json paths: ${HOME}/.adk/...)
# HOME is /root
RUN mkdir -p /root/.adk/adk-python
COPY tools/adk_knowledge_ext/tests/integration/common/dummy_ranked_targets.yaml /root/.adk/ranked_targets.yaml

# 3. Method 2: Extension Installation Simulator
COPY tools/adk_knowledge_ext/tests/integration/method2/install_extension.py /app/install.py

# Run the installer (reads /tmp/pkg/gemini-extension.json -> writes ~/.gemini/settings.json)
RUN python /app/install.py

# 4. Verification
COPY tools/adk_knowledge_ext/tests/integration/common/verify_mcp_config.py /app/verify.py

CMD ["python", "/app/verify.py"]
