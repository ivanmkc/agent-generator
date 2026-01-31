#!/bin/bash
# Mock Claude CLI
# Log calls to /tmp/claude_log

echo "claude $*" >> /tmp/claude_log

if [[ "$*" == "mcp list" ]]; then
    # Return existence of server if it was added
    if grep -q "mcp add codebase-knowledge" /tmp/claude_log; then
        echo "codebase-knowledge: env ..."
    else
        echo "No MCP servers."
    fi
fi
