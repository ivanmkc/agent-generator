ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG EXTENSION_REPO=https://github.com/derailed-dash/adk-docs-ext
ARG EXTENSION_REF=main

USER root

# Set config dir environment variable so extension installs to the right place
ENV GEMINI_CONFIG_DIR=/root/.gemini/

# Copy settings.json
COPY settings.json /root/.gemini/settings.json

# Install the extension
RUN if [ -z "$EXTENSION_REF" ] || [ "$EXTENSION_REF" = "main" ]; then \
      yes Y | gemini extensions install ${EXTENSION_REPO} --consent; \
    else \
      yes Y | gemini extensions install ${EXTENSION_REPO} --ref ${EXTENSION_REF} --consent; \
    fi

# Create a symbolic link
RUN ln -s /usr/local/bin/uv /root/.local/bin/uv

# Install mcpdoc permanently to avoid uvx startup latency
RUN /root/.local/bin/uv tool install mcpdoc

# Add uv tools to path
ENV PATH="/root/.local/bin:$PATH"

# Create alias for hallucinated command 'adk-docs-mcp' pointing to mcpdoc
# This fixes "bash: adk-docs-mcp: command not found" when the model tries to use the server name as a CLI tool.
RUN ln -s /root/.local/bin/mcpdoc /usr/local/bin/adk-docs-mcp

# Update gemini-extension.json to use the installed mcpdoc and absolute paths
COPY patch_config.py /tmp/patch_config.py
RUN python3 /tmp/patch_config.py

# Set working directory to /app
WORKDIR /workdir
