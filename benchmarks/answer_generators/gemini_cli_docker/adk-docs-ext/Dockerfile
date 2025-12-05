ARG BASE_IMAGE=gemini-cli-base
FROM ${BASE_IMAGE}

USER root

# Install the extension
# The gemini cli should be installed in the base image.
# We install the extension which will be available for the 'gemini' command.
RUN gemini extensions install https://github.com/derailed-dash/adk-docs-ext
