"""
Verification script for Managed Setup (JSON Integration).

Tests the `codebase-knowledge-mcp-manage` CLI tool's ability to detect and 
configure IDEs that use JSON config files (e.g., Cursor, Windsurf).
It mocks the file system structure and verifies JSON updates.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def main():
    print("--- Starting Managed JSON Setup Verification ---")
    
    # Mock Cursor directory and config
    cursor_dir = Path.home() / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    mcp_config_path = cursor_dir / "mcp.json"
    
    initial_config = {"mcpServers": {"existing-server": {"command": "echo", "args": ["hi"]}}}
    with open(mcp_config_path, "w") as f:
        json.dump(initial_config, f)
        
    # 1. Setup
    print("Running setup...")
    cmd = [
        "codebase-knowledge-mcp-manage", "setup",
        "--repo-url", "https://github.com/test/repo.git",
        "--version", "v1.0.0",
        "--api-key", "fake-key",
        "--force"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Setup failed: {e}")
        sys.exit(1)
        
    # Verify Config
    with open(mcp_config_path, "r") as f:
        config = json.load(f)
        
    print(f"Config after setup:\n{json.dumps(config, indent=2)}")
    
    if "codebase-knowledge" in config.get("mcpServers", {}):
        server_config = config["mcpServers"]["codebase-knowledge"]
        if server_config["command"] == "uvx" and "fake-key" in server_config["env"]["GEMINI_API_KEY"]:
            print("SUCCESS: JSON config updated correctly.")
        else:
            print("FAIL: Config content mismatch.")
            sys.exit(1)
    else:
        print("FAIL: Server not added to mcpServers.")
        sys.exit(1)

    # 2. Remove
    print("Running remove...")
    cmd_remove = ["codebase-knowledge-mcp-manage", "remove"]
    
    # Pipe 'y' for confirmation
    p = subprocess.Popen(cmd_remove, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(input="y\n")
    
    if p.returncode != 0:
        print(f"Remove failed: {stderr}")
        sys.exit(1)

    # Verify Removal
    with open(mcp_config_path, "r") as f:
        config = json.load(f)
        
    print(f"Config after remove:\n{json.dumps(config, indent=2)}")
    
    if "codebase-knowledge" not in config.get("mcpServers", {}):
        if "existing-server" in config["mcpServers"]:
            print("SUCCESS: Server removed, existing config preserved.")
        else:
            print("FAIL: Existing config was wiped.")
            sys.exit(1)
    else:
        print("FAIL: Server was not removed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
