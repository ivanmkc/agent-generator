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
      echo "Y" | gemini extensions install ${EXTENSION_REPO}; \
    else \
      echo "Y" | gemini extensions install ${EXTENSION_REPO} --ref ${EXTENSION_REF}; \
    fi

# Create a symbolic link
RUN ln -s /usr/local/bin/uv /root/.local/bin/uv

# Set working directory to /app
WORKDIR /workdir
