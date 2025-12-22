# Inherit from the standard ADK Python image
ARG BASE_IMAGE=gemini-cli:adk-python
FROM ${BASE_IMAGE}

# Switch to root to install system deps if needed (usually not for pure python)
USER root

# Install the MCP SDK
# We assume 'uv' is available from the base image
RUN uv pip install --system mcp

# Install adk-python in standard mode (not editable) so it's properly installed in site-packages
# The source code is already cloned in /workdir/repos/adk-python by the base image.
RUN uv pip install --system /workdir/repos/adk-python \
    # Also install common development dependencies if adk-python doesn't bring them
    # For a robust agent execution, ensure common dev tools like pytest, black, ruff are available
    && uv pip install --system pytest black ruff \
    # Clean up uv cache to reduce image size
    && uv clean

# Copy the MCP server source code
COPY src/ /src/mcp-server/

# Configure the Gemini CLI to use this MCP server
# We overwrite (or merge) the existing settings.json
COPY settings.json /root/.gemini/settings.json

# Overwrite INSTRUCTIONS.md with the MCP-specific version
COPY INSTRUCTIONS_MCP_RUNNER.md /workdir/INSTRUCTIONS.md

# Ensure the server script is executable
RUN chmod +x /src/mcp-server/adk_runner_server.py

# Verify ADK installation (checking for google.adk namespace)
RUN python3 -c "import sys; print(sys.path); import google.adk.agents.base_agent; print('ADK (google.adk) successfully imported')"

# Set the final working directory
WORKDIR /workdir

# Switch back to non-root user if desired, though Gemini CLI often runs as root in these containers
# USER node 
