#!/bin/bash
# Mock gemini CLI
# It logs arguments to /tmp/gemini_mock.log

echo "gemini $@" >> /tmp/gemini_mock.log

if [[ "$2" == "list" ]]; then
    if [[ -f /tmp/gemini_configured ]]; then
        echo "Configured MCP servers:"
        echo "codebase-knowledge"
    else
        echo "No MCP servers configured."
    fi
elif [[ "$2" == "add" ]]; then
    touch /tmp/gemini_configured
elif [[ "$2" == "remove" ]]; then
    rm -f /tmp/gemini_configured
fi
