ARG BASE_IMAGE=gemini-cli-base
FROM ${BASE_IMAGE}

# Set working directory
WORKDIR /app

# Install gettext-base for envsubst
RUN apt-get update && apt-get install -y --no-install-recommends gettext-base && rm -rf /var/lib/apt/lists/*

# Create the /etc/gemini-cli directory and copy the settings.json template
RUN mkdir -p /etc/gemini-cli/
COPY settings.json /etc/gemini-cli/settings.json.template

# Copy an entrypoint script that performs env var substitution
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
