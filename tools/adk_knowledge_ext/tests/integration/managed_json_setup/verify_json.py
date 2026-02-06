"""
Verification script for Managed Setup (JSON Integration).

Tests the `codebase-knowledge-mcp-manage` CLI tool's ability to detect and 
configure multiple IDEs that use JSON config files (Cursor).
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def main():
    print("--- Starting Multi-IDE Managed JSON Setup Verification ---")
    
    home = Path.home()
    ide_configs = [
        {"name": "Cursor", "dir": home / ".cursor", "file": "mcp.json"},
    ]
    
    # Initialize all IDEs with existing configs
    for ide in ide_configs:
        ide["dir"].mkdir(parents=True, exist_ok=True)
        initial_config = {"mcpServers": {"existing-server": {"command": "echo", "args": [ide["name"]]}}}
        with open(ide["dir"] / ide["file"], "w") as f:
            json.dump(initial_config, f)
        print(f"Initialized {ide['name']} at {ide['dir'] / ide['file']}")

    # 1. Setup
    print("\nRunning setup for all detected IDEs...")
    cmd = [
        "codebase-knowledge-mcp-manage", "setup",
        "--repo-url", "https://github.com/test/repo.git",
        "--version", "v1.0.0",
        "--force"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Setup failed: {e}")
        sys.exit(1)
        
    # Verify All Configs
    for ide in ide_configs:
        path = ide["dir"] / ide["file"]
        with open(path, "r") as f:
            config = json.load(f)
        
        if "codebase-knowledge" in config.get("mcpServers", {}):
            print(f"{ide['name']} config updated.")
        else:
            print(f"{ide['name']} server not added.")
            sys.exit(1)

    # 2. Remove
    print("\nRunning remove...")
    # Pipe 'y' for each IDE removal confirmation
    # We have 1 IDE detected, so we need 1 'y' plus the initial 'Remove from:' choices.
    # Actually 'force' isn't on remove, but we can pipe multiple y's.
    # The tool asks:
    # 1. Remove from IDE 1? [Y/n]
    # ...
    confirmations = "y\n" * 10 
    p = subprocess.Popen(["codebase-knowledge-mcp-manage", "remove"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = p.communicate(input=confirmations)
    
    if p.returncode != 0:
        print(f"Remove failed: {stderr}")
        sys.exit(1)

    # Verify All Removals
    for ide in ide_configs:
        path = ide["dir"] / ide["file"]
        with open(path, "r") as f:
            config = json.load(f)
        
        if "codebase-knowledge" not in config.get("mcpServers", {}):
            if "existing-server" in config["mcpServers"]:
                print(f"{ide['name']} server removed, existing config preserved.")
            else:
                print(f"{ide['name']} existing config was wiped.")
                sys.exit(1)
        else:
            print(f"{ide['name']} server was not removed.")
            sys.exit(1)

    print("\nAll JSON-based IDE tests PASSED.")

if __name__ == "__main__":
    main()