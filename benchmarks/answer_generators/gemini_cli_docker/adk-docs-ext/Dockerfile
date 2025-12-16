ARG BASE_IMAGE
FROM ${BASE_IMAGE}

USER root

# Install gettext-base for envsubst
RUN apt-get update && apt-get install -y --no-install-recommends gettext-base && rm -rf /var/lib/apt/lists/*

# Create the /root/.gemini/ directory and copy the settings.json template
RUN mkdir -p /root/.gemini/
COPY settings.json.template /root/.gemini/settings.json.template

# Copy the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set config dir environment variable so extension installs to the right place
ENV GEMINI_CONFIG_DIR=/root/.gemini/

# Install the extension
RUN echo "Y" | gemini extensions install https://github.com/derailed-dash/adk-docs-ext

# Set working directory to /app (common practice for standalone apps)
WORKDIR /app

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]