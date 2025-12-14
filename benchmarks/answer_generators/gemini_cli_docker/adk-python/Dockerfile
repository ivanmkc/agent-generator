# Allow overriding the base image (e.g. for Cloud Build)
ARG BASE_IMAGE=adk-gemini-sandbox:base
FROM ${BASE_IMAGE}

# Create repos directory
RUN mkdir -p /repos

# Clone the adk-python repository into /repos/adk-python
RUN git clone https://github.com/google/adk-python.git /repos/adk-python

# Copy the GEMINI.md for context
COPY GEMINI.md /repos/adk-python/GEMINI.md

# Write version.txt from build argument
ARG VERSION=unknown
RUN echo "${VERSION}" > /repos/version.txt

# Set the final working directory to /repos
WORKDIR /repos

# Switch back to a non-root user
USER node
