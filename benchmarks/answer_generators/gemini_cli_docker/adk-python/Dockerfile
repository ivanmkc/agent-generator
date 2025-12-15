# Allow overriding the base image (e.g. for Cloud Build)
ARG BASE_IMAGE=adk-gemini-sandbox:base
FROM ${BASE_IMAGE}

# Create repos directory
RUN mkdir -p /repos

# Create working directory
RUN mkdir -p /workdir

# Clone the adk-python repository into /repos/adk-python
RUN git clone https://github.com/google/adk-python.git /repos/adk-python

# Create the GEMINI_CONFIG_DIR and copy settings.json
RUN mkdir -p /tmp/.gemini/
COPY --chown=node:node adk-python/settings.json /workdir/.gemini/settings.json

# Copy the INSTRUCTIONS.md for context
COPY --chown=node:node INSTRUCTIONS.md /workdir/INSTRUCTIONS.md

# Write version.txt from build argument
ARG VERSION=unknown
RUN echo "${VERSION}" > /workdir/version.txt

# Set the final working directory to /workdir/
WORKDIR /workdir

# Switch back to a non-root user
USER node
