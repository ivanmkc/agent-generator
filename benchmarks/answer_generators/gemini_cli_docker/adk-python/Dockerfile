# Allow overriding the base image (e.g. for Cloud Build)
ARG BASE_IMAGE=adk-gemini-sandbox:base
FROM ${BASE_IMAGE}

# Create repos directory
RUN mkdir -p /repos

# Clone the adk-python repository into /repos/adk-python
RUN git clone https://github.com/google/adk-python.git /repos/adk-python

# Copy version.txt if it exists (in the build context) to the working directory
# Note: We assume version.txt is in the context root (adk-python dir)
COPY version.txt /repos/version.txt

# Set the final working directory to /repos
WORKDIR /repos

# Switch back to a non-root user
USER node
