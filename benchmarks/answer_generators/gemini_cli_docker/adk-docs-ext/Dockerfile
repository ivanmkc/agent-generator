ARG BASE_IMAGE
FROM ${BASE_IMAGE}

USER root

# Set config dir environment variable so extension installs to the right place
ENV GEMINI_CONFIG_DIR=/root/.gemini/

# Copy settings.json
COPY settings.json /root/.gemini/settings.json

# Install the extension
RUN echo "Y" | gemini extensions install https://github.com/derailed-dash/adk-docs-ext

# Create a symbolic link
RUN ln -s /usr/local/bin/uv /root/.local/bin/uv

# Set working directory to /app (common practice for standalone apps)
WORKDIR /app
