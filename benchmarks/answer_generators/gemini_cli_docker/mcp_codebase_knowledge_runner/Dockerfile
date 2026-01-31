ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

USER root

# Install git/curl/uv for the server setup
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 1. Setup Build Context
COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/index.yaml

# IMPORTANT: Set these BEFORE pip install so hatch_build.py can bundle them into instructions
ENV TARGET_REPO_URL="https://github.com/google/adk-python.git"
ENV TARGET_VERSION="v1.20.0"
ENV TARGET_INDEX_URL="file:///tmp/index.yaml"

# 2. Install Package (Bundles index and dynamic instructions)
COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 3. Pre-seed Instructions
# We place the instructions where the server expects them, so the CLI can find them via settings
RUN INSTR_PATH=$(python3 -c "import adk_knowledge_ext; from pathlib import Path; print(Path(adk_knowledge_ext.__file__).parent / 'data' / 'INSTRUCTIONS.md')") && \
    mkdir -p /root/.mcp_cache/instructions && \
    cp "$INSTR_PATH" /root/.mcp_cache/instructions/adk-python.md

ENV GEMINI_API_KEY=dummy_for_build

# 4. Automated Configuration via Manage Tool
# We ensure the config directory exists so detection works
RUN mkdir -p /root/.gemini
# We run the setup tool. Note: We use the installed package via its script.
# We pass --force to skip prompts.
# We pass repo-url/version to match the environment.
# Since 'gemini' command might not be in PATH if it's a node tool not linked, we might need to handle that.
# Assuming 'gemini' is in PATH.
RUN codebase-knowledge-mcp-manage setup \
    --repo-url "https://github.com/google/adk-python.git" \
    --version "v1.20.0" \
    --api-key "dummy_key" \
    --force

# 5. Fix Context Path in Generated Settings
# The manage tool doesn't yet support injecting 'context.fileName'.
# So we need to append it manually or update the manage tool.
# Updating the manage tool is better. But for now, let's use jq or python to patch it.
RUN python3 -c "import json; f='/root/.gemini/settings.json'; d=json.load(open(f)); d['context']={'fileName': ['/root/.mcp_cache/instructions/adk-python.md'], 'includeDirectories': ['/workdir'], 'loadMemoryFromIncludeDirectories': True}; json.dump(d, open(f,'w'))"

WORKDIR /workdir