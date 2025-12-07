ARG BASE_IMAGE=adk-gemini-sandbox:base
FROM ${BASE_IMAGE}

USER root

# Install gettext-base for envsubst
RUN apt-get update && apt-get install -y --no-install-recommends gettext-base && rm -rf /var/lib/apt/lists/*

# Create the /etc/gemini-cli directory and copy the settings.json template
RUN mkdir -p /etc/gemini-cli/
COPY settings.json.template /etc/gemini-cli/settings.json.template

# Copy the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Install the extension
RUN gemini extensions install https://github.com/derailed-dash/adk-docs-ext

# Set working directory to /app (common practice for standalone apps)
WORKDIR /app

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]