ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

# Create working directory
RUN mkdir -p /workdir

# Copy the adk_skill directory into the image
COPY ../../../../adk_skill /workdir/adk_skill

# Copy the instructions.txt for context
COPY ../../../../adk_skill/instructions.txt /workdir/instructions.txt

# Write version.txt from build argument
ARG VERSION=unknown
RUN echo "${VERSION}" > /workdir/version.txt

# Set the final working directory to /workdir/
WORKDIR /workdir
