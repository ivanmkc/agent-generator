# Use the official Gemini CLI base image for realistic testing
FROM gemini-cli:base

WORKDIR /app

# The base image already has node, gemini-cli, and uv installed.
# We just need to install our package and run the verification.

# 1. Install Package
COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 2. Make management script explicitly executable (it's installed in site-packages)
RUN chmod +x /usr/local/lib/python3.11/site-packages/adk_knowledge_ext/manage_mcp.py

# 3. Verification Script
COPY tools/adk_knowledge_ext/tests/integration/managed_setup/verify_managed_setup.py /app/verify.py

# Override base image CMD
CMD ["python", "/app/verify.py"]