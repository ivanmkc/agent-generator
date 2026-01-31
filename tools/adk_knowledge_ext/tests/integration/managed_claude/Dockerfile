FROM python:3.10-slim

WORKDIR /app

# Install git/curl
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Install package
COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# Setup Mock Claude
COPY tools/adk_knowledge_ext/tests/integration/managed_claude/mock_claude.sh /usr/local/bin/claude
RUN chmod +x /usr/local/bin/claude

# Verification script
COPY tools/adk_knowledge_ext/tests/integration/managed_claude/verify_claude.py /app/verify.py

CMD ["python", "/app/verify.py"]
