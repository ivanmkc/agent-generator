FROM python:3.10-slim

WORKDIR /app

# 1. Install Dependencies
COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 2. Setup Data (Corrupt)
RUN mkdir -p /data/adk-python
# Create a file that is NOT valid YAML
RUN echo "this: is: [invalid yaml" > /data/corrupt_index.yaml

# 3. Verification Script
COPY tools/adk_knowledge_ext/tests/integration/method3/verify_resilience.py /app/verify.py

CMD ["python", "/app/verify.py"]
