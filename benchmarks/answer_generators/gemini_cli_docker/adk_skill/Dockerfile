ARG BASE_IMAGE=gemini-cli:base
FROM ${BASE_IMAGE}

# Create working directory
RUN mkdir -p /workdir

# Copy the adk_skill directory into the image
COPY . /workdir/adk_skill

# Copy the settings.json into the adk_skill directory in the image
COPY settings.json /workdir/adk_skill/settings.json

# Write version.txt from build argument
ARG VERSION=unknown
RUN echo "${VERSION}" > /workdir/version.txt

# Set the final working directory to /workdir/
WORKDIR /workdir
