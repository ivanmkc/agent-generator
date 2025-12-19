# Allow overriding the base image (e.g. for Cloud Build)
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# Create repos directory
RUN mkdir -p /repos

# Create working directory
RUN mkdir -p /workdir

# Initialize git to ensure project root detection
RUN cd /workdir && git init

# Clone the adk-python repository into /repos/adk-python
RUN git clone --branch v1.20.0 https://github.com/google/adk-python.git /workdir/repos/adk-python

# Create the GEMINI_CONFIG_DIR and copy settings.json
RUN mkdir -p /tmp/.gemini/
COPY --chown=node:node settings.json /workdir/.gemini/settings.json

# Copy the INSTRUCTIONS.md for context
COPY --chown=node:node INSTRUCTIONS.md /workdir/INSTRUCTIONS.md

# Write version.txt from build argument
ARG VERSION=unknown
RUN echo "${VERSION}" > /workdir/version.txt

# Set the final working directory to /workdir/
WORKDIR /workdir

# Switch back to a non-root user
USER node
