ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

USER root

# Install git/curl for the server's runtime cloning capabilities
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# 1. Setup Build Context
COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/index.yaml

# IMPORTANT: Set these BEFORE pip install so hatch_build.py can bundle them into instructions
ENV TARGET_REPO_URL="https://github.com/google/adk-python.git"
ENV TARGET_VERSION="v1.20.0"
ENV TARGET_INDEX_URL="file:///tmp/index.yaml"

# 2. Install Package (Bundles index and dynamic instructions)
COPY tools/adk_knowledge_ext /tmp/pkg
RUN pip install /tmp/pkg

# 3. Configure Gemini CLI to use the BUNDLED instructions
# We find the path to the installed package's data directory
RUN INSTR_PATH=$(python3 -c "import adk_knowledge_ext; from pathlib import Path; print(Path(adk_knowledge_ext.__file__).parent / 'data' / 'INSTRUCTIONS.md')") && \
    ln -s "$INSTR_PATH" /workdir/INSTRUCTIONS.md

ENV GEMINI_SYSTEM_MD=/workdir/INSTRUCTIONS.md
ENV GEMINI_API_KEY=dummy_for_build

# 4. Gemini CLI Settings
COPY benchmarks/answer_generators/gemini_cli_docker/mcp_codebase_knowledge_runner/settings.json /root/.gemini/settings.json

WORKDIR /workdir
