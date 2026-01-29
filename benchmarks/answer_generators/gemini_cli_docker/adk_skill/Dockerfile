ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

# Create working directory
RUN mkdir -p /workdir

# Copy the adk_skill directory into the image
COPY . /workdir/adk_skill

# Initialize git to ensure project root detection (like adk-python)
RUN cd /workdir && git init

# Create the .gemini directory and copy settings.json
RUN mkdir -p /workdir/.gemini
COPY settings.json /workdir/.gemini/settings.json

# Write version.txt from build argument
ARG VERSION=unknown
RUN echo "${VERSION}" > /workdir/version.txt

# Set the final working directory to /workdir/
WORKDIR /workdir
