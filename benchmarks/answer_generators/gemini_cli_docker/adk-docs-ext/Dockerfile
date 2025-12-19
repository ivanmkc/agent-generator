ARG BASE_IMAGE
FROM ${BASE_IMAGE}

USER root

# Install gettext-base for envsubst
RUN apt-get update && apt-get install -y --no-install-recommends gettext-base && rm -rf /var/lib/apt/lists/*

# Set config dir environment variable so extension installs to the right place
ENV GEMINI_CONFIG_DIR=/root/.gemini/

# Install the extension
RUN echo "Y" | gemini extensions install https://github.com/derailed-dash/adk-docs-ext

# Create a symbolic link
RUN ln -s /usr/local/bin/uv /root/.local/bin/uv

# Set working directory to /app (common practice for standalone apps)
WORKDIR /app
