FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
RUN pip install hatchling pyyaml

# Create dummy index (As a YAML list)
RUN echo "[{id: 'bundled.symbol', type: 'class', docstring: 'Bundled content'}]" > /tmp/dummy_index.yaml

# Copy package source
COPY tools/adk_knowledge_ext /tmp/pkg

# Configure Registry to point to dummy index
# We overwrite registry.yaml inside the source before build
RUN mkdir -p /tmp/pkg/src/adk_knowledge_ext
RUN echo "https://bundled.com/repo.git:\n  v1.0.0: file:///tmp/dummy_index.yaml" > /tmp/pkg/src/adk_knowledge_ext/registry.yaml

# Install (triggers hatch_build.py)
# We need to set TARGET_REPO_URL/VERSION env vars just in case hatch hook needs them for fallback, 
# but the new logic iterates the registry regardless.
RUN pip install /tmp/pkg

# Setup runtime env
ENV TARGET_REPO_URL=https://bundled.com/repo.git
ENV TARGET_VERSION=v1.0.0
# NO TARGET_INDEX_URL

# Copy verification script
COPY tools/adk_knowledge_ext/tests/integration/bundled_index/verify_bundled.py /app/verify.py

CMD ["python", "/app/verify.py"]
