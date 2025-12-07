# Base image
FROM python:3.11-slim-bookworm

# Switch to root to install packages and Python environment
USER root

# Install git, curl, ca-certificates, gnupg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22.x (LTS)
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv (https://astral.sh/uv/install.sh)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv

# Install Python dependencies for the server (FastAPI/Uvicorn)
RUN pip install --no-cache-dir fastapi uvicorn

# Install Gemini CLI
RUN npm install -g @google/gemini-cli

# Copy the CLI server wrapper
COPY cli_server.py /usr/local/bin/cli_server.py
RUN chmod +x /usr/local/bin/cli_server.py

# Create node user for compatibility (variants can switch to this user)
RUN useradd -m -u 1000 node