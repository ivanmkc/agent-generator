import json
import os
from pathlib import Path

settings_path = Path("/root/.gemini/settings.json")
if not settings_path.exists():
    print(f"Error: {settings_path} not found.")
    exit(1)

with open(settings_path, "r") as f:
    data = json.load(f)

mcp_servers = data.setdefault("mcpServers", {})
mcp_servers["adk-agent-runner"] = {
    "command": "python3",
    "args": ["/app/agent-runner/adk_runner_server.py"]
}

with open(settings_path, "w") as f:
    json.dump(data, f, indent=2)
print("Successfully patched settings.json")
