ARG BASE_IMAGE=gemini-cli-base
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

# Create /repos directory and clone the repository
RUN mkdir -p /repos
RUN git clone https://github.com/google/adk-python.git /repos/adk-python

# Copy the context file
COPY GEMINI.md /repos/GEMINI.md

# Set working directory to /repos where GEMINI.md is located
WORKDIR /repos

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]