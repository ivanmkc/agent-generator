ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# Set working directory
WORKDIR /workdir

# Create the /etc/gemini-cli directory and copy the settings.json template
RUN mkdir -p /root/.gemini/
COPY settings.json /root/.gemini/settings.json
COPY system.md /root/.gemini/system.md
ENV GEMINI_SYSTEM_MD=/root/.gemini/system.md

